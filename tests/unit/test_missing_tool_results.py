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

"""
Tests for the Missing Tool Results Handler functionality.

These tests verify that add_missing_tool_results() correctly handles situations
where tool invocations lack corresponding results.
"""

from unittest.mock import MagicMock

from mypy_boto3_bedrock_runtime.type_defs import MessageUnionTypeDef

from generative_ai_toolkit.agent import BedrockConverseAgent


def test_add_missing_tool_results_with_missing_results():
    """Test that missing tool results are filled in with error results."""
    # Setup: User message followed by assistant message with tool use (no tool results)
    messages: list[MessageUnionTypeDef] = [
        {
            "role": "user",
            "content": [{"text": "What's the weather?"}],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool-123",
                        "name": "get_weather",
                        "input": {"city": "Seattle"},
                    }
                }
            ],
        },
    ]

    # Create agent with a mock bedrock client to avoid AWS credential requirements
    mock_client = MagicMock()
    agent = BedrockConverseAgent(model_id="test-model", bedrock_client=mock_client)
    result = agent.add_missing_tool_results(messages)

    # Verify: Should modify the user message to add error tool result
    assert len(result) == 2
    assert result[0]["role"] == "user"
    # Should have original text plus error tool result
    assert len(result[0]["content"]) == 2
    # Use .get() for optional TypedDict keys
    assert result[0]["content"][0].get("text") == "What's the weather?"

    tool_result = result[0]["content"][1].get("toolResult")
    assert tool_result is not None
    assert tool_result["toolUseId"] == "tool-123"
    assert tool_result.get("status") == "error"
    assert tool_result.get("content") == [{"text": "Failed to get tool result"}]


def test_add_missing_tool_results_pass_through():
    """Test that messages with complete tool results are passed through unchanged."""
    # Setup: Create messages with tool use AND corresponding tool results
    messages: list[MessageUnionTypeDef] = [
        {
            "role": "user",
            "content": [{"text": "What's the weather?"}],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool-123",
                        "name": "get_weather",
                        "input": {"city": "Seattle"},
                    }
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool-123",
                        "status": "success",
                        "content": [{"text": "Sunny, 75°F"}],
                    }
                }
            ],
        },
    ]

    # Create agent with a mock bedrock client to avoid AWS credential requirements
    mock_client = MagicMock()
    agent = BedrockConverseAgent(model_id="test-model", bedrock_client=mock_client)
    result = agent.add_missing_tool_results(messages)

    # Verify: Should return the same messages (no changes)
    assert len(result) == 3
    assert result == messages


def test_add_missing_tool_results_error_format():
    """Test that error results have the correct format."""
    # Setup: User message followed by assistant message with multiple tool uses but no results
    messages: list[MessageUnionTypeDef] = [
        {
            "role": "user",
            "content": [{"text": "Do two things"}],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": "tool_a",
                        "input": {},
                    }
                },
                {
                    "toolUse": {
                        "toolUseId": "tool-2",
                        "name": "tool_b",
                        "input": {},
                    }
                },
            ],
        },
    ]

    # Create agent with a mock bedrock client to avoid AWS credential requirements
    mock_client = MagicMock()
    agent = BedrockConverseAgent(model_id="test-model", bedrock_client=mock_client)
    result = agent.add_missing_tool_results(messages)

    # Verify: Should modify the user message to add error results for both tools
    assert len(result) == 2
    user_message = result[0]
    assert user_message["role"] == "user"
    # Should have original text plus 2 error tool results
    assert len(user_message["content"]) == 3

    # Check both error results have the correct format
    tool_use_ids = set()
    for content_block in user_message["content"][1:]:  # Skip the original text
        tool_result = content_block.get("toolResult")
        assert tool_result is not None
        tool_use_ids.add(tool_result["toolUseId"])
        assert tool_result.get("status") == "error"
        assert tool_result.get("content") == [{"text": "Failed to get tool result"}]

    # Verify both tool IDs are present
    assert tool_use_ids == {"tool-1", "tool-2"}
