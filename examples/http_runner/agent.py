from generative_ai_toolkit.agent import BedrockConverseAgent
from generative_ai_toolkit.run.agent import Runner
from generative_ai_toolkit.test.mock import MockBedrockConverse


def response_generator(mock: MockBedrockConverse, _):
    mock.add_output(
        "Day 2 is stasis. Followed by irrelevance. Followed by excruciating, painful decline. Followed by death. And that is why it is always Day 1."
    )


mock = MockBedrockConverse(
    response_generator=response_generator, stream_delay_between_tokens=0.2
)


def agent_factory():
    return BedrockConverseAgent(
        model_id="dummy",
        bedrock_client=mock.client(),
    )


Runner.configure(
    agent=agent_factory, auth_context_fn=lambda _: {"principal_id": "test"}
)
