# Architecture diagrams

Referenced from the root [README.md](../../README.md).

- `hydrosense-overall.png` — the full HydroSense system: Arduino water-level sensing and gateway (designed, not yet streaming), rainfall/historical data sources, backend risk assessment, community reports, image upload, Bedrock assessment, storage, and dashboard.
- `hydrosense-aws.png` — the AWS-only deployed infrastructure: CloudFront, S3, API Gateway, Lambda, DynamoDB, the private evidence bucket, Bedrock, and IAM boundaries.
