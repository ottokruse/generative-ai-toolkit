# Copyright 2025 Amazon.com, Inc. and its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import threading
from collections.abc import Callable, Iterable, Sequence
from contextvars import ContextVar
from typing import (
    Any,
    Literal,
    Protocol,
    TypedDict,
    Unpack,
    cast,
    overload,
)

from flask import Flask, Request, Response, request
from pydantic import BaseModel, ConfigDict, Field

from generative_ai_toolkit.agent.tool import Tool
from generative_ai_toolkit.context import AuthContext
from generative_ai_toolkit.tracer.trace import Trace
from generative_ai_toolkit.utils.json import DefaultJsonEncoder
from generative_ai_toolkit.utils.logging import logger


class Runnable(Protocol):
    @property
    def conversation_id(self) -> str: ...

    def set_conversation_id(self, conversation_id: str) -> None: ...

    def set_auth_context(self, **auth_context: Unpack[AuthContext]) -> None: ...

    def reset(self) -> None: ...

    @overload
    def converse_stream(
        self,
        user_input: str,
        stream: Literal["text"] = "text",
        tools: Sequence[Tool] | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterable[str]:
        """
        Start or continue a conversation with the agent.

        Response fragments (text chunks) are yielded as they are produced.

        The caller must consume this iterable fully for the agent to progress.

        The iterable ends when the agent requests new user input, and then you should call this function again with the new user input.

        If you provide tools, that list of tools supersedes any tools that have been registered with the agent (but otherwise does not force their use).

        The agent may decide to use tools, and will do so autonomously (limited by the max_successive_tool_invocations that you've set on the agent).
        """
        ...

    @overload
    def converse_stream(
        self,
        user_input: str,
        stream: Literal["traces"],
        tools: Sequence[Tool] | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterable[Trace]:
        """
        Start or continue a conversation with the agent.

        Traces are yielded as they are produced by the agent and its tools.

        The caller must consume this iterable fully for the agent to progress.

        The iterable ends when the agent requests new user input, and then you should call this function again with the new user input.

        If you provide tools, that list of tools supersedes any tools that have been registered with the agent (but otherwise does not force their use).

        The agent may decide to use tools, and will do so autonomously (limited by the max_successive_tool_invocations that you've set on the agent).
        """
        ...


class Body(BaseModel):
    model_config = ConfigDict(extra="allow")
    user_input: str = Field(
        description="The input from the user to the agent", min_length=1
    )
    stream: Literal["text", "traces"] = Field(
        default="text", description="Response stream type"
    )


AuthContextFn = Callable[[Request], AuthContext]

TraceMapFn = Callable[[Request, Body, Trace], Any]


class RunnerConfig(TypedDict, total=False):
    agent: Runnable | Callable[[], Runnable]
    auth_context_fn: AuthContextFn
    trace_map_fn: TraceMapFn


def iam_auth_context_fn(request: Request) -> AuthContext:
    try:
        amzn_request_context = json.loads(request.headers["x-amzn-request-context"])
        principal_id = amzn_request_context["authorizer"]["iam"]["userId"]
        return {"principal_id": principal_id, "extra": amzn_request_context}
    except Exception as e:
        raise Exception("Missing AWS IAM Auth context") from e


class _Runner:
    _agent: Runnable | Callable[[], Runnable] | None
    _auth_context_fn: AuthContextFn
    _trace_map_fn: TraceMapFn
    _app: Flask

    def __init__(self) -> None:
        self._agent = None
        self._auth_context_fn = iam_auth_context_fn
        self._trace_map_fn = lambda request, body, trace: trace
        self._context = ContextVar[Runnable | None]("agent", default=None)

    @property
    def agent(self) -> Runnable:
        if not self._agent:
            raise ValueError("Agent not configured yet")
        # Cache an agent instance in each context:
        context_agent = self._context.get()
        if not context_agent:
            if callable(self._agent):
                context_agent = self._agent()
            else:
                context_agent = self._agent
            self._context.set(context_agent)
        return context_agent

    @property
    def auth_context_fn(self) -> AuthContextFn:
        return self._auth_context_fn

    @property
    def trace_map_fn(self) -> TraceMapFn:
        return self._trace_map_fn

    def configure(
        self,
        **kwargs: Unpack[RunnerConfig],
    ):
        if "agent" in kwargs:
            self._agent = kwargs["agent"]
        if "auth_context_fn" in kwargs:
            if not callable(kwargs["auth_context_fn"]):
                raise ValueError("auth_context_fn must be callable")
            self._auth_context_fn = kwargs["auth_context_fn"]
        if "trace_map_fn" in kwargs:
            if not callable(kwargs["trace_map_fn"]):
                raise ValueError("trace_map_fn must be callable")
            self._trace_map_fn = kwargs["trace_map_fn"]

    @property
    def app(self):
        app = Flask(__name__)

        @app.get("/")
        def health():
            return "Up and running! To chat with the agent, use HTTP POST"

        @app.post("/")
        def index():
            agent = self.agent

            try:
                auth_context = self.auth_context_fn(request)
                agent.set_auth_context(**auth_context)
            except Exception as err:
                logger.warn(f"Forbidden: {err}")
                return Response("Forbidden", status=403)

            try:
                body = Body.model_validate_json(request.data)
            except Exception as err:
                logger.info(f"Unprocessable entity: {err}")
                return Response("Unprocessable entity", status=422)

            x_conversation_id = request.headers.get("x-conversation-id")
            if x_conversation_id:
                agent.set_conversation_id(x_conversation_id)
            else:
                agent.reset()

            stop_event = threading.Event()

            # Explicitly consume the first chunk so any obvious errors (e.g. insufficient IAM permissions)
            # bubble up before we return status 200 below
            chunks = agent.converse_stream(
                body.user_input, stream=body.stream, stop_event=stop_event
            )
            first_chunk = next(iter(chunks))

            def _chunks_or_traces():
                try:
                    yield first_chunk
                    yield from chunks
                finally:
                    # In case the iterator isn't fully consumed and the caller breaks off the HTTP request:
                    stop_event.set()

            def chunked_reponse():
                try:
                    if body.stream == "traces":
                        for trace in _chunks_or_traces():
                            mapped_trace = self.trace_map_fn(
                                request, body, cast(Trace, trace)
                            )
                            if mapped_trace is not None:
                                yield json.dumps(
                                    mapped_trace,
                                    cls=DefaultJsonEncoder,
                                ) + "\n"
                    else:
                        for chunk in _chunks_or_traces():
                            yield cast(str, chunk)
                except Exception:
                    logger.exception()
                    yield json.dumps(
                        {"error": {"message": "An internal server error occurred"}}
                    )

            return Response(
                chunked_reponse(),
                status=200,
                content_type=(
                    "text/plain; charset=utf-8"
                    if body.stream == "text"
                    else "application/x-ndjson; charset=utf-8"
                ),
                headers={
                    "x-conversation-id": agent.conversation_id,
                    "transfer-encoding": "chunked",
                    "Cache-Control": "no-cache",
                },
            )

        @app.errorhandler(Exception)
        def error(error):
            logger.exception()
            return "Internal Server Error", 500

        return app

    def __call__(self):
        """
        Making the runner callable makes it easy to use the Runner object directly,
        when launching e.g. gunicorn from the CLI:

        gunicorn path.to.myagent:Runner()
        """
        return self.app


Runner = _Runner()
