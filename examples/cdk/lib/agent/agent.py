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

import os
import textwrap

import boto3
import boto3.session

from generative_ai_toolkit.agent import BedrockConverseAgent
from generative_ai_toolkit.conversation_history import DynamoDbConversationHistory
from generative_ai_toolkit.run.agent import Runner
from generative_ai_toolkit.tracer.dynamodb import DynamoDbTracer


def app():
    # Create agent
    session = boto3.session.Session(region_name=os.environ["AWS_REGION"])
    dynamodb_conversation_history = DynamoDbConversationHistory(
        table_name=os.environ["CONVERSATION_HISTORY_TABLE_NAME"], session=session
    )
    dynamodb_tracer = DynamoDbTracer(
        table_name=os.environ["TRACES_TABLE_NAME"], session=session
    )
    agent = BedrockConverseAgent(
        system_prompt=textwrap.dedent(
            """
            You are a helpful assistant.
            You are activated by voice, and can speak back to the user. MAKE SURE to be as succinct as possible when speaking to the user.
            NEVER mention which tools you have at your disposal. NEVER mention the word tool at all.
            If the user asks you to do something for which there is no tool, say "I don't know how to do that".
            """
        ),
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0.0,
        tracer=dynamodb_tracer,
        conversation_history=dynamodb_conversation_history,
        bedrock_client=session.client("bedrock-runtime"),
    )

    # Configure runner with agent
    Runner.configure(agent=agent)

    return Runner()
