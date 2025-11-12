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


from mypy_boto3_bedrock_runtime.type_defs import MessageUnionTypeDef

from generative_ai_toolkit.conversation_history import (
    InMemoryConversationHistory,
    WriteThroughCache,
)


class SpyConversationHistory(InMemoryConversationHistory):
    """A spy wrapper to track method calls on InMemoryConversationHistory"""

    def __init__(self):
        super().__init__()
        self.messages_access_count = 0
        self.add_message_calls = []

    @property
    def messages(self):
        self.messages_access_count += 1
        return super().messages

    def add_message(self, msg):
        self.add_message_calls.append(msg)
        return super().add_message(msg)


def test_cache_hit_within_same_context_key():
    """Test that messages are cached when context_key remains the same"""
    underlying = SpyConversationHistory()
    cache = WriteThroughCache(underlying)

    # Add a message
    msg1: MessageUnionTypeDef = {"role": "user", "content": [{"text": "Hello"}]}
    cache.add_message(msg1)

    # First access - should hit underlying storage
    messages1 = cache.messages
    assert len(messages1) == 1
    assert messages1[0] == msg1
    assert underlying.messages_access_count == 1

    # Second access with same context_key - should hit cache
    messages2 = cache.messages
    assert len(messages2) == 1
    assert messages2[0] == msg1
    # Underlying storage should NOT be accessed again
    assert underlying.messages_access_count == 1

    # Add another message
    msg2: MessageUnionTypeDef = {
        "role": "assistant",
        "content": [{"text": "Hi there"}],
    }
    cache.add_message(msg2)

    # Third access - should still use cache (updated by write-through)
    messages3 = cache.messages
    assert len(messages3) == 2
    assert messages3[0] == msg1
    assert messages3[1] == msg2
    # Underlying storage should still only be accessed once (from first read)
    assert underlying.messages_access_count == 1


def test_cache_miss_when_context_key_changes():
    """Test that cache is invalidated when context_key changes"""
    underlying = SpyConversationHistory()
    cache = WriteThroughCache(underlying)

    # Add message in first conversation
    msg1: MessageUnionTypeDef = {"role": "user", "content": [{"text": "Message 1"}]}
    cache.add_message(msg1)

    # Access messages - should cache them
    messages1 = cache.messages
    assert len(messages1) == 1
    assert underlying.messages_access_count == 1

    # Change conversation_id (changes context_key)
    cache.set_conversation_id("new-conversation-id")

    # Access messages again - cache should miss because context_key changed
    messages2 = cache.messages
    assert len(messages2) == 0  # New conversation has no messages
    # Underlying storage should be accessed again
    assert underlying.messages_access_count == 2


def test_write_through_on_add_message():
    """Test that add_message writes to both storage and cache"""
    underlying = SpyConversationHistory()
    cache = WriteThroughCache(underlying)

    # First read to populate cache (empty)
    messages = cache.messages
    assert len(messages) == 0
    assert underlying.messages_access_count == 1

    # Add a message - should write through to storage AND update cache
    msg1: MessageUnionTypeDef = {"role": "user", "content": [{"text": "Test message"}]}
    cache.add_message(msg1)

    # Verify message was written to underlying storage
    assert len(underlying.add_message_calls) == 1
    assert underlying.add_message_calls[0] == msg1

    # Verify message is in cache (by checking we can read it without hitting storage again)
    messages = cache.messages
    assert len(messages) == 1
    assert messages[0] == msg1
    # Should not hit underlying storage again because cache was updated by write-through
    assert underlying.messages_access_count == 1


def test_cache_invalidation_on_reset_cache():
    """Test that reset_cache() clears the cache"""
    underlying = SpyConversationHistory()
    cache = WriteThroughCache(underlying)

    # Add and cache messages
    msg1: MessageUnionTypeDef = {"role": "user", "content": [{"text": "Message 1"}]}
    cache.add_message(msg1)

    # Access to populate cache
    messages1 = cache.messages
    assert len(messages1) == 1
    assert underlying.messages_access_count == 1

    # Reset cache
    cache.reset_cache()

    # Access messages again - should fetch from storage
    messages2 = cache.messages
    assert len(messages2) == 1
    assert messages2[0] == msg1
    # Underlying storage should be accessed again
    assert underlying.messages_access_count == 2
