# Minimal AWS Integration Plan

## Status

AWS DynamoDB persistence, hosted FastAPI backend, and S3/CloudFront frontend were **implemented and verified on 2026-10-10** in `ap-south-1`. Local JSON remains the default development backend; DynamoDB is enabled explicitly with `STORAGE_BACKEND=dynamodb`. No hardware, AWS IoT or SNS milestone is implied by this simulator-backed proof.

The `hydrosense-data-dev` CloudFormation stack manages these active, encrypted, on-demand tables:

- `hydrosense-readings-dev`
- `hydrosense-incidents-dev`

The stack is defined in `infrastructure/dynamodb.yaml`. Its stateful resources deliberately use `DeletionPolicy: Delete` and `UpdateReplacePolicy: Delete` because this is an ephemeral hackathon environment scheduled for teardown, not a production retention policy.

The `hydrosense-api-dev` SAM/CloudFormation stack manages:

- API Gateway HTTP API: `https://0795acig2g.execute-api.ap-south-1.amazonaws.com`
- Lambda function: `hydrosense-api-dev-api`
- A dedicated execution role restricted to the two table ARNs and function log delivery
- API access and Lambda log groups with seven-day retention

The stack is defined in `infrastructure/backend.yaml`. The public demo API is throttled to 10 requests per second with a burst of 20. It is not a production-authenticated endpoint.

The `hydrosense-frontend-dev` CloudFormation stack manages:

- Private encrypted S3 origin with all public access blocked
- CloudFront distribution using origin access control and HTTPS redirects
- SPA fallback routing and security response headers
- Dashboard URL: `https://d348efecbg3b7i.cloudfront.net`

## First cloud milestone

Add a DynamoDB implementation of the existing `StorageRepository` protocol and select it with configuration. Keep threshold processing, incident creation, duplicate suppression, API schemas and frontend contracts unchanged.

The first proof is intentionally limited to software persistence:

1. FastAPI receives the existing `SensorReading` payload.
2. The DynamoDB repository stores the reading and any generated incident.
3. A test reads the exact records directly from DynamoDB with the AWS SDK.
4. The API is restarted and can still return the cloud-backed records.

AWS IoT Core, SNS and S3 are not prerequisites for this first proof. They should be added only when their corresponding workflow is ready to test end to end. The submitted project still requires genuine, demonstrable AWS use.

## Minimum resources

- One DynamoDB readings table: `hydrosense-readings-dev`.
- One DynamoDB incidents table: `hydrosense-incidents-dev`.
- One application IAM principal or execution role restricted to those two tables.
- API Gateway HTTP API and one on-demand Python 3.12 Lambda function.
- CloudWatch access and function log groups with seven-day retention.

For hackathon-scale data, the first adapter may use bounded `Scan` operations to preserve the current repository interface. Add keys/indexes and purpose-specific query methods only after the cloud proof identifies a demonstrated need. Do not treat this as a production-scale design.

## Configuration

```text
STORAGE_BACKEND=json|dynamodb
AWS_REGION=ap-south-1
DYNAMODB_READINGS_TABLE=hydrosense-readings-dev
DYNAMODB_INCIDENTS_TABLE=hydrosense-incidents-dev
```

Use the standard AWS SDK credential provider chain. For local development, use an authenticated AWS profile or short-lived environment credentials supplied outside the repository. Do not add access keys, session tokens, phone numbers or certificates to `.env.example`, source code, logs or Git.

## Runtime IAM permissions

Restrict resources to the two exact table ARNs and allow only:

- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:UpdateItem`
- `dynamodb:Scan`
- `dynamodb:DescribeTable`

The runtime role must not create or delete tables. Provisioning credentials may separately use `dynamodb:CreateTable`, `dynamodb:UpdateTable`, `dynamodb:DescribeTable` and tagged-resource deletion during controlled teardown.

## Verification gate

Use a unique test run ID and a clearly simulated reading. The AWS milestone passes only when all of these are recorded:

1. `aws sts get-caller-identity` confirms the intended account and role without printing secrets.
2. Both tables report `ACTIVE` in the intended region.
3. FastAPI starts with `STORAGE_BACKEND=dynamodb` and ingests the simulator payload with HTTP 201.
4. A separate AWS SDK assertion reads the stored reading directly from DynamoDB and matches `device_id`, `location_id`, depth, distance, timestamp and `source: simulated_sensor`.
5. For an above-threshold reading, a separate assertion finds one corresponding high-water incident and confirms duplicate suppression.
6. After a backend restart, the API returns the same reading and incident.
7. The test run ID, region, table names, sanitized command output and CloudWatch evidence (if deployed) are saved in the demo notes.

Do not report AWS integration complete if the API only writes to local JSON, if the record is visible only through a mock, or if direct AWS readback fails.

### Verified result: 2026-10-10

- SSO profile `hydrosense-dev` assumed the intended `AdministratorAccess` role; no static keys were added to the repository.
- CloudFormation stack status: `CREATE_COMPLETE`.
- Both tables reported `ACTIVE`, `PAY_PER_REQUEST` and server-side encryption `ENABLED`.
- Three simulator readings were accepted through FastAPI with HTTP 201 and read directly from DynamoDB.
- The first two high readings were 325 seconds apart and correctly created two incidents. A third reading 8 seconds later was stored while the incident count remained two, proving the 300-second duplicate cooldown.
- After stopping and starting FastAPI, the API returned all three readings and both open incidents from DynamoDB.
- Full backend suite: 16 passed. Local `cfn-lint` and `cfn-guard` were unavailable; CloudFormation service validation and a reviewed change set passed before deployment.

### Hosted backend result: 2026-10-10

- SAM stack `hydrosense-api-dev` reached `CREATE_COMPLETE` after a reviewed seven-resource change set.
- Lambda `hydrosense-api-dev-api` reported `Active` with Python 3.12, 512 MB memory, a 10-second timeout and `STORAGE_BACKEND=dynamodb`.
- `GET /health` returned HTTP 200 and the existing service/version contract through API Gateway.
- The hosted API returned the three records created during local verification, proving cloud reads.
- A 29 cm simulator reading sent to the hosted endpoint returned HTTP 201; direct DynamoDB counts then showed four readings and three incidents.
- Browser CORS preflight returned HTTP 200 for `http://localhost:5173` with GET, POST, PATCH and OPTIONS allowed.
- Runtime IAM readback showed only `DescribeTable`, `GetItem`, `PutItem`, `Scan` and `UpdateItem` on the two exact table ARNs; it cannot create or delete tables.
- Lambda logs contained successful invocations with no runtime errors. The first cold start initialized in about 1.36 seconds; warm calls completed in 35-88 ms and used 118 MB at peak.
- API access logs recorded GET 200, POST 201 and OPTIONS 200 with no integration errors.
- Full backend suite: 17 passed. The Lambda adapter event test and SAM/cfn-lint validation passed before deployment. `cfn-guard` was unavailable, so a separate automated compliance ruleset was not run.

### Hosted frontend result: 2026-10-10

- Stack `hydrosense-frontend-dev` reached `CREATE_COMPLETE` with private S3, CloudFront OAC and no public bucket access.
- The Vite production build uses the deployed API Gateway URL and is synchronized to the private bucket.
- CloudFront returned HTTP 200 with CSP, HSTS, frame-deny, content-type and referrer-policy headers.
- Backend CORS was updated in place to allow only `https://d348efecbg3b7i.cloudfront.net` as the deployed browser origin.
- Desktop (1440x900) and mobile (390x844) browser checks rendered live DynamoDB data with no console errors, failed requests or horizontal overflow.
- CloudWatch logs are active; CloudWatch alarms are intentionally deferred to a later step.

## Cleanup

After the hackathon, remove compute before data:

```powershell
$bucket = aws cloudformation describe-stacks --stack-name hydrosense-frontend-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text
aws s3 rm "s3://$bucket" --recursive --region ap-south-1 --profile hydrosense-dev
aws cloudformation delete-stack --stack-name hydrosense-frontend-dev --region ap-south-1 --profile hydrosense-dev
aws cloudformation wait stack-delete-complete --stack-name hydrosense-frontend-dev --region ap-south-1 --profile hydrosense-dev
sam delete --stack-name hydrosense-api-dev --region ap-south-1 --profile hydrosense-dev --no-prompts
aws cloudformation delete-stack --stack-name hydrosense-data-dev --region ap-south-1 --profile hydrosense-dev
aws cloudformation wait stack-delete-complete --stack-name hydrosense-data-dev --region ap-south-1 --profile hydrosense-dev
```

Do not delete tables, functions or APIs individually because that would leave their CloudFormation stacks out of sync. SAM also created the shared `aws-sam-cli-managed-default` artifact stack; remove it with `sam delete` only when no other SAM application uses that bucket.

## Later, separately verified steps

- AWS IoT Core MQTT for the physical ESP32 after Rasleen completes local wiring and calibration.
- SNS alert delivery after sandbox/recipient constraints are resolved.
- S3 only for real source datasets or analysis artifacts that the demo actually uses.
- CloudWatch alarms for Lambda errors/throttles and API 5xx responses.
