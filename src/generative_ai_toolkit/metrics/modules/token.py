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

from generative_ai_toolkit.metrics import BaseMetric, Measurement, Unit


class TokensMetric(BaseMetric):
    def evaluate_trace(self, trace, **kwargs):
        if trace.attributes.get("ai.trace.type") != "llm-invocation":
            return

        input_tokens = trace.attributes["ai.llm.response.usage"]["inputTokens"]
        output_tokens = trace.attributes["ai.llm.response.usage"]["outputTokens"]

        return [
            Measurement(
                name="TotalTokens",
                value=input_tokens + output_tokens,
                unit=Unit.Count,
            ),
            Measurement(
                name="InputTokens",
                value=input_tokens,
                unit=Unit.Count,
            ),
            Measurement(
                name="OutputTokens",
                value=output_tokens,
                unit=Unit.Count,
            ),
        ]
