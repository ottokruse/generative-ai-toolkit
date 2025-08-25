import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StreamingAgent } from "./agent";
import * as path from "path";


export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const AGENT_MODEL = cdk.aws_bedrock.FoundationModel.fromFoundationModelId(
      this,
      "ModelRef",
      new cdk.aws_bedrock.FoundationModelIdentifier(
        "anthropic.claude-3-sonnet-20240229-v1:0"
      )
    );

    const EVAL_MODEL = cdk.aws_bedrock.FoundationModel.fromFoundationModelId(
      this,
      "ModelRef",
      cdk.aws_bedrock.FoundationModelIdentifier
        .ANTHROPIC_CLAUDE_3_SONNET_20240229_V1_0
    );

    const agent = new StreamingAgent(this, "MyAgent", {
      agentCode: cdk.aws_lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "agent")
      ),
      evaluationCode: cdk.aws_lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "evaluation")
      ),
      agentModels: [AGENT_MODEL],
      evaluationModels: [EVAL_MODEL],
    });
  }
}
