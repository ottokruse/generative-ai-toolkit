# Open Telemetry tracing

To run a local collector to forward traces to AWS X-ray, you can use [AWS Distro for OpenTelemetry (ADOT)](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-adot.html).

Follow the below steps.

## 1. Create configuration file

Create a file `adot-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch/traces:
    timeout: 10s
    send_batch_size: 50

exporters:
  awsxray:
    region: eu-central-1
    indexed_attributes:
      - ai.conversation.id

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch/traces]
      exporters: [awsxray]
```

## 2. Run the `adot-collector` docker container

Ensure you have exported the AWS environment variables:

```shell
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=... # optional, for temporary credentials
```

Those AWS credentials must map to a user/role that has permissions to create traces in AWS X-Ray:

```json
{
  "Effect": "Allow",
  "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
  "Resource": "*"
}
```

Then, start the container, that will listen on `localhost:4318`:

```shell
docker run --rm --name adot-collector \
  -p 4318:4318 \
  -e AWS_REGION=eu-central-1 \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -v $(pwd)/adot-config.yaml:/etc/collector-config.yaml \
  public.ecr.aws/aws-observability/aws-otel-collector:latest \
  --config=/etc/collector-config.yaml
```

# 3. Send some traces

```python
from generative_ai_toolkit.tracer import Trace
from generative_ai_toolkit.tracer.otlp import OtlpTracer
tracer = OtlpTracer()
tracer.persist(Trace("my-trace"))
```
