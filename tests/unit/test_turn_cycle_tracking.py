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
Test for Turn/Cycle Tracking functionality.

This module tests the _calculate_turn_nr() method which is responsible for
determining the current turn number based on the conversation history.
"""

from mypy_boto3_bedrock_runtime.type_defs import MessageUnionTypeDef

from generative_ai_toolkit.agent.bedrock_converse_agent import BedrockConverseAgent


def test_calculate_turn_nr_comprehensive():
    """
    Test _calculate_turn_nr with various message sequences.

    Turn number should be:
    - The count of completed assistant messages (without toolUse)
    - 0-based counting
    - Tool use messages (assistant messages with toolUse) should not be counted
    """

    # Test 1: Empty messages list
    assert BedrockConverseAgent._calculate_turn_nr([]) == 0

    # Test 2: User message only
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Hello"}]}
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 0

    # Test 3: User + assistant message (no tools)
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 1

    # Test 4: Multiple user/assistant message pairs
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
        {"role": "assistant", "content": [{"text": "I'm doing well!"}]},
        {"role": "user", "content": [{"text": "Great!"}]},
        {"role": "assistant", "content": [{"text": "Glad to hear!"}]},
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 3

    # Test 5: Assistant message with toolUse should NOT be counted
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "What's the weather?"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "123",
                        "name": "get_weather",
                        "input": {"location": "NYC"},
                    }
                }
            ],
        },
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 0

    # Test 6: Mixed scenario - assistant with text, assistant with toolUse, assistant with text
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi!"}]},  # Turn 1
        {"role": "user", "content": [{"text": "What's the weather?"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "123",
                        "name": "get_weather",
                        "input": {"location": "NYC"},
                    }
                }
            ],
        },  # Not counted (has toolUse)
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "123", "content": [{"text": "Sunny"}]}}
            ],
        },
        {"role": "assistant", "content": [{"text": "It's sunny!"}]},  # Turn 2
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 2

    # Test 7: Multiple tool uses in sequence (common in multi-tool scenarios)
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Get weather and time"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "123",
                        "name": "get_weather",
                        "input": {"location": "NYC"},
                    }
                },
                {
                    "toolUse": {
                        "toolUseId": "456",
                        "name": "get_time",
                        "input": {"timezone": "EST"},
                    }
                },
            ],
        },  # Not counted (has toolUse)
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "123", "content": [{"text": "Sunny"}]}},
                {"toolResult": {"toolUseId": "456", "content": [{"text": "3pm"}]}},
            ],
        },
        {
            "role": "assistant",
            "content": [{"text": "It's sunny and 3pm!"}],
        },  # Turn 1
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 1

    # Test 8: Assistant message with both text and toolUse should NOT be counted
    # (edge case - some models might return both)
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": "Check the weather"}]},
        {
            "role": "assistant",
            "content": [
                {"text": "Let me check that for you."},
                {
                    "toolUse": {
                        "toolUseId": "123",
                        "name": "get_weather",
                        "input": {"location": "NYC"},
                    }
                },
            ],
        },  # Not counted (has toolUse)
    ]
    assert BedrockConverseAgent._calculate_turn_nr(messages) == 0
