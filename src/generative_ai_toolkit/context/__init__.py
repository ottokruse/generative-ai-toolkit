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

# This is in this separate file so it can be imported by both agents and tools
# without running into circular imports


import contextvars
from collections.abc import Hashable, Sequence
from threading import Event
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict, cast

from generative_ai_toolkit.tracer import NoopTracer, Tracer
from generative_ai_toolkit.utils.ulid import Ulid

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import MessageUnionTypeDef

    # Prevent circular import by doing this only during TYPE_CHECKING:
    from generative_ai_toolkit.agent import Agent


class AuthContext(TypedDict):
    principal_id: str | None
    """
    The ID of the principal (e.g. the user) that the agent is acting on behalf of
    """

    # Once https://peps.python.org/pep-0728 lands (Python 3.15?) we can deprecate this property,
    # as the TypedDict would then allow extra keys itself.
    extra: NotRequired[Any]
    """
    Additional information to add to the AuthContext
    """

class AgentContext:

    _current = contextvars.ContextVar["AgentContext"]("agent_context")

    conversation_id: str
    """The conversation ID"""

    subcontext_id: str | None
    """The subcontext ID"""

    tracer: Tracer
    """The tracer that is used by the agent; tools can use it for adding their own traces"""

    auth_context: AuthContext
    """The auth context; tools can use it for enforcing authentication and authorization"""

    stop_event: Event
    """
    Stop event (threading) that may be set to signal abortion; tools that run for a longer span of time
    should consult the stop event regularly (`stop_event.is_set()`) and abort early if it is set
    """

    context_key: "Hashable"
    """The context key; tools can use it for advanced purposes such as caching results per unique context"""

    messages: Sequence["MessageUnionTypeDef"]
    """
    The messages exchanged in the current conversation so far
    """

    agent: "Agent"
    """
    Reference to the agent instance that is executing the tool; tools can use this reference for intricate operations
    such as registering new tools dynamically
    """

    cycle_nr: int
    """
    The current cycle number within a turn (0-based). A cycle represents one iteration of the agent's
    reasoning loop, which may include an LLM invocation and optional tool executions.
    """

    turn_nr: int
    """
    The current turn number in the conversation (0-based). A turn encompasses all cycles needed
    to generate a complete response to user input, starting from 0 for the first turn.
    """

    def __init__(
        self,
        *,
        conversation_id: str,
        subcontext_id: str | None = None,
        tracer: Tracer,
        auth_context: AuthContext,
        agent: "Agent",
        stop_event: Event | None,
        context_key: "Hashable | None" = None,
        messages: Sequence["MessageUnionTypeDef"] = (),
        cycle_nr: int = 0,
        turn_nr: int = 0,
    ) -> None:
        self.conversation_id = conversation_id
        self.subcontext_id = subcontext_id
        self.tracer = tracer
        self.auth_context = auth_context
        self.stop_event = stop_event or Event()
        self.context_key = context_key or Ulid()
        self.agent = agent
        self.messages = messages
        self.cycle_nr = cycle_nr
        self.turn_nr = turn_nr

    @classmethod
    def current(cls) -> "AgentContext":
        """
        Access the current agent context from within a tool invocation
        """
        return cls._current.get()

    def copy_context(self):
        ctx = contextvars.copy_context()
        ctx.run(lambda: self._current.set(self))
        return ctx

    @classmethod
    def set_test_context(
        cls,
        *,
        conversation_id: str = "test",
        subcontext_id: str | None = None,
        auth_context: AuthContext | None = None,
        tracer: Tracer | None = None,
        stop_event: Event | None = None,
        agent: "Agent | None" = None,
        messages: Sequence["MessageUnionTypeDef"] = (),
        cycle_nr: int = 0,
        turn_nr: int = 0,
    ) -> "AgentContext":
        """
        Helper function to set up a test AgentContext for use in test fixtures.

        Parameters
        ----------
        conversation_id : str, optional
            The conversation ID for testing, by default "test"
        subcontext_id : str, optional
            The subcontext ID for testing, by default None
        auth_context : AuthContext, optional
            The AuthContext for testing, by default AuthContext(principal_id="test")
        tracer : Tracer, optional
            The tracer to use, by default NoopTracer()
        stop_event : Event, optional
            The stop event to use, by default None
        agent : Agent, optional
            The agent to use, by default a DummyAgent
        messages : Sequence["MessageUnionTypeDef"]
            The messages exchanged in the conversation so far
        cycle_nr : int, optional
            The current cycle number, by default 0
        turn_nr : int, optional
            The current turn number, by default 0

        Returns
        -------
        AgentContext
            The configured test context that has been set as current
        """

        class DummyAgent:
            def __getattr__(self, name: str) -> Any:
                raise NotImplementedError

            def __setattr__(self, name: str, value: Any) -> None:
                raise NotImplementedError

        context = cls(
            conversation_id=conversation_id,
            subcontext_id=subcontext_id,
            tracer=tracer or NoopTracer(),
            auth_context=(
                auth_context.copy()
                if auth_context
                else AuthContext(principal_id="test")
            ),
            stop_event=stop_event,
            agent=agent or cast("Agent", DummyAgent()),
            messages=messages,
            cycle_nr=cycle_nr,
            turn_nr=turn_nr,
        )
        cls._current.set(context)
        return context
