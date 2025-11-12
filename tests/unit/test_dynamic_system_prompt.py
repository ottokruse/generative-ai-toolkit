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


from generative_ai_toolkit.agent import BedrockConverseAgent
from generative_ai_toolkit.context import AgentContext


def test_static_string_system_prompt_still_works(mock_bedrock_converse):
    """Test that static string system_prompt still works (backward compatibility)"""
    static_prompt = "You are a helpful assistant that always responds politely."

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=static_prompt,
    )

    mock_bedrock_converse.add_output("Hello! I'm here to help.")
    agent.converse("Hi there")

    # Verify the static system prompt was sent in the LLM request
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 1
    llm_request_system = llm_invocation_traces[0].attributes.get(
        "ai.llm.request.system"
    )
    assert llm_request_system is not None
    assert llm_request_system == [{"text": static_prompt}]


def test_callable_system_prompt_receives_agent_context(mock_bedrock_converse):
    """Test that callable system_prompt receives correct AgentContext"""
    received_contexts = []

    def dynamic_system_prompt(context: AgentContext) -> str:
        # Capture the context for inspection
        received_contexts.append(
            {
                "conversation_id": context.conversation_id,
                "auth_context": context.auth_context,
                "cycle_nr": context.cycle_nr,
                "turn_nr": context.turn_nr,
                "messages": context.messages,
                "agent": context.agent,
            }
        )
        return f"You are on turn {context.turn_nr}, cycle {context.cycle_nr}"

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=dynamic_system_prompt,
    )

    # Set up auth context and conversation id
    test_conversation_id = "test-conversation-123"
    test_auth_context = {"principal_id": "test-user"}
    agent.set_conversation_id(test_conversation_id)
    agent.set_auth_context(**test_auth_context)

    mock_bedrock_converse.add_output("Response 1")
    agent.converse("First message")

    # Verify context was passed correctly
    assert len(received_contexts) == 1
    ctx = received_contexts[0]

    assert ctx["conversation_id"] == test_conversation_id
    assert ctx["auth_context"] == test_auth_context
    assert ctx["cycle_nr"] == 0  # First cycle
    assert ctx["turn_nr"] == 0  # First turn (no assistant messages yet)
    assert ctx["agent"] is agent
    assert len(ctx["messages"]) == 1  # User message added
    assert ctx["messages"][0]["role"] == "user"


def test_callable_system_prompt_invoked_per_cycle(mock_bedrock_converse):
    """Test that callable system_prompt is invoked once per cycle"""
    invocation_count = 0
    cycle_numbers = []

    def dynamic_system_prompt(context: AgentContext) -> str:
        nonlocal invocation_count
        invocation_count += 1
        cycle_numbers.append(context.cycle_nr)
        return f"Cycle {context.cycle_nr}"

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=dynamic_system_prompt,
    )

    # Set up a scenario with multiple cycles (tool use)
    def dummy_tool() -> str:
        """A simple tool"""
        return "tool result"

    agent.register_tool(dummy_tool)

    # Cycle 0: LLM decides to use tool
    mock_bedrock_converse.add_output(
        tool_use_output={"name": "dummy_tool", "input": {}}
    )
    # Cycle 1: LLM provides final response
    mock_bedrock_converse.add_output("Final response")

    agent.converse("Test message")

    # Verify system_prompt was invoked twice (once per cycle)
    assert invocation_count == 2
    assert cycle_numbers == [0, 1]

    # Verify the system prompts were used in LLM requests
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 2

    # Check first cycle
    assert llm_invocation_traces[0].attributes["ai.llm.request.system"] == [
        {"text": "Cycle 0"}
    ]

    # Check second cycle
    assert llm_invocation_traces[1].attributes["ai.llm.request.system"] == [
        {"text": "Cycle 1"}
    ]


def test_system_prompt_can_access_context_attributes(mock_bedrock_converse):
    """Test that system_prompt can access turn_nr, cycle_nr, messages from context"""
    captured_context = None

    def context_aware_system_prompt(context: AgentContext) -> str:
        nonlocal captured_context
        captured_context = context

        # Access various context attributes
        turn_nr = context.turn_nr
        cycle_nr = context.cycle_nr
        messages = context.messages
        message_count = len(messages)

        return (
            f"Turn: {turn_nr}, Cycle: {cycle_nr}, "
            f"Messages in history: {message_count}"
        )

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=context_aware_system_prompt,
    )

    mock_bedrock_converse.add_output("Response 1")
    agent.converse("First message")

    # Verify all context attributes are accessible
    assert captured_context is not None
    assert hasattr(captured_context, "turn_nr")
    assert hasattr(captured_context, "cycle_nr")
    assert hasattr(captured_context, "messages")
    assert hasattr(captured_context, "agent")
    assert hasattr(captured_context, "conversation_id")
    assert hasattr(captured_context, "auth_context")
    assert hasattr(captured_context, "tracer")
    assert hasattr(captured_context, "stop_event")
    assert hasattr(captured_context, "context_key")

    # Verify the system prompt reflected the context
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 1
    system_prompt_text = llm_invocation_traces[0].attributes["ai.llm.request.system"][
        0
    ]["text"]
    assert "Turn: 0" in system_prompt_text
    assert "Cycle: 0" in system_prompt_text
    assert "Messages in history: 1" in system_prompt_text


def test_system_prompt_changes_across_turns(mock_bedrock_converse):
    """Test that system_prompt can dynamically change across multiple turns"""

    def turn_aware_system_prompt(context: AgentContext) -> str:
        if context.turn_nr == 0:
            return "This is the first turn. Be brief."
        elif context.turn_nr == 1:
            return "This is the second turn. Provide more detail."
        else:
            return f"This is turn {context.turn_nr}. Be comprehensive."

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=turn_aware_system_prompt,
    )

    # Turn 0
    mock_bedrock_converse.add_output("Brief response")
    agent.converse("Message 1")

    # Turn 1
    mock_bedrock_converse.add_output("Detailed response")
    agent.converse("Message 2")

    # Turn 2
    mock_bedrock_converse.add_output("Comprehensive response")
    agent.converse("Message 3")

    # Verify different system prompts were used
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 3

    assert llm_invocation_traces[0].attributes["ai.llm.request.system"] == [
        {"text": "This is the first turn. Be brief."}
    ]
    assert llm_invocation_traces[1].attributes["ai.llm.request.system"] == [
        {"text": "This is the second turn. Provide more detail."}
    ]
    assert llm_invocation_traces[2].attributes["ai.llm.request.system"] == [
        {"text": "This is turn 2. Be comprehensive."}
    ]


def test_system_prompt_with_converse_stream(mock_bedrock_converse):
    """Test that callable system_prompt works with converse_stream"""
    invocation_count = 0

    def dynamic_system_prompt(context: AgentContext) -> str:
        nonlocal invocation_count
        invocation_count += 1
        return f"Stream cycle {context.cycle_nr}"

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=dynamic_system_prompt,
    )

    mock_bedrock_converse.add_output("Streamed response")

    # Consume the stream
    response = "".join(agent.converse_stream("Test message"))

    assert response == "Streamed response\n"
    assert invocation_count == 1

    # Verify the system prompt was used
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 1
    assert llm_invocation_traces[0].attributes["ai.llm.request.system"] == [
        {"text": "Stream cycle 0"}
    ]


def test_none_system_prompt(mock_bedrock_converse):
    """Test that None system_prompt works (no system prompt sent)"""
    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        system_prompt=None,
    )

    mock_bedrock_converse.add_output("Response without system prompt")
    agent.converse("Test message")

    # Verify no system prompt was sent
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 1
    assert (
        "ai.llm.request.system" not in llm_invocation_traces[0].attributes
        or llm_invocation_traces[0].attributes["ai.llm.request.system"] is None
    )
