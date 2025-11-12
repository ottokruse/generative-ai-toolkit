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
from generative_ai_toolkit.agent.tool import Tool
from generative_ai_toolkit.context import AgentContext


def test_tool_filter_receives_correct_parameters(mock_bedrock_converse):
    """Test that tool_filter receives correct AgentContext, tool_name, and tool"""
    captured_calls = []

    def tool_a():
        """Tool A"""
        return "A"

    def tool_b():
        """Tool B"""
        return "B"

    def custom_filter(context: AgentContext, tool_name: str, tool: Tool) -> bool:
        # Capture all parameters for inspection
        captured_calls.append(
            {
                "context": context,
                "tool_name": tool_name,
                "tool": tool,
            }
        )
        return True

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        tools=[tool_a, tool_b],
        tool_filter=custom_filter,
    )

    # Set up test context
    test_conversation_id = "test-conversation-123"
    test_auth_context = {"principal_id": "test-user"}
    agent.set_conversation_id(test_conversation_id)
    agent.set_auth_context(**test_auth_context)

    mock_bedrock_converse.add_output("Response")
    agent.converse("Test message")

    # Verify tool_filter was called for each tool
    assert len(captured_calls) == 2

    # Check first call (tool_a)
    call1 = captured_calls[0]
    assert isinstance(call1["context"], AgentContext)
    assert call1["context"].conversation_id == test_conversation_id
    assert call1["context"].auth_context == test_auth_context
    assert call1["context"].agent is agent
    assert call1["context"].turn_nr == 0
    assert call1["context"].cycle_nr == 0
    assert call1["tool_name"] == "tool_a"
    assert isinstance(call1["tool"], Tool)
    assert call1["tool"].tool_spec["name"] == "tool_a"

    # Check second call (tool_b)
    call2 = captured_calls[1]
    assert call2["tool_name"] == "tool_b"
    assert call2["tool"].tool_spec["name"] == "tool_b"


def test_tool_filter_excludes_tools_when_returns_false(mock_bedrock_converse):
    """Test that tools are excluded when filter returns False"""

    def tool_a():
        """Tool A"""
        return "A"

    def tool_b():
        """Tool B"""
        return "B"

    def tool_c():
        """Tool C"""
        return "C"

    def exclude_tool_b(context: AgentContext, tool_name: str, tool: Tool) -> bool:
        # Exclude tool_b
        return tool_name != "tool_b"

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        tools=[tool_a, tool_b, tool_c],
        tool_filter=exclude_tool_b,
    )

    mock_bedrock_converse.add_output("Response")
    agent.converse("Test message")

    # Verify only tool_a and tool_c are included
    llm_invocation_traces = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
    ]

    assert len(llm_invocation_traces) == 1
    tool_config = llm_invocation_traces[0].attributes.get("ai.llm.request.tool.config")
    assert tool_config is not None
    assert len(tool_config["tools"]) == 2
    tool_names = {tool["toolSpec"]["name"] for tool in tool_config["tools"]}
    assert tool_names == {"tool_a", "tool_c"}
    assert "tool_b" not in tool_names


def test_dynamic_filtering_based_on_turn_nr(mock_bedrock_converse):
    """Test dynamic filtering based on turn_nr"""

    def beginner_tool():
        """Tool for beginners"""
        return "Beginner result"

    def advanced_tool():
        """Tool for advanced users"""
        return "Advanced result"

    def turn_based_filter(context: AgentContext, tool_name: str, tool: Tool) -> bool:
        # Only show advanced_tool after turn 0
        if tool_name == "advanced_tool":
            return context.turn_nr > 0
        return True

    agent = BedrockConverseAgent(
        model_id="dummy",
        session=mock_bedrock_converse.session(),
        tools=[beginner_tool, advanced_tool],
        tool_filter=turn_based_filter,
    )

    # Turn 0: Only beginner_tool should be available
    mock_bedrock_converse.add_output("Response 1")
    agent.converse("First message")

    llm_traces_turn_0 = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
        and trace.attributes.get("ai.turn.nr") == 0
    ]

    assert len(llm_traces_turn_0) == 1
    tool_config_turn_0 = llm_traces_turn_0[0].attributes.get(
        "ai.llm.request.tool.config"
    )
    assert tool_config_turn_0 is not None
    tool_names_turn_0 = {
        tool["toolSpec"]["name"] for tool in tool_config_turn_0["tools"]
    }
    assert tool_names_turn_0 == {"beginner_tool"}

    # Turn 1: Both tools should be available
    mock_bedrock_converse.add_output("Response 2")
    agent.converse("Second message")

    llm_traces_turn_1 = [
        trace
        for trace in agent.traces
        if trace.attributes.get("ai.trace.type") == "llm-invocation"
        and trace.attributes.get("ai.turn.nr") == 1
    ]

    assert len(llm_traces_turn_1) == 1
    tool_config_turn_1 = llm_traces_turn_1[0].attributes.get(
        "ai.llm.request.tool.config"
    )
    assert tool_config_turn_1 is not None
    tool_names_turn_1 = {
        tool["toolSpec"]["name"] for tool in tool_config_turn_1["tools"]
    }
    assert tool_names_turn_1 == {"beginner_tool", "advanced_tool"}
