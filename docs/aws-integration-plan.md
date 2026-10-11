# Minimal AWS Integration Plan

## Status

AWS DynamoDB persistence, hosted FastAPI, and an S3/CloudFront frontend were **implemented and verified on 2026-10-10** in `ap-south-1`. That historical deployment is still the pre-integration vertical slice. Local JSON remains the default development backend; DynamoDB is enabled explicitly with `STORAGE_BACKEND=dynamodb`. No hardware, AWS IoT, SNS, Bedrock, or reviewed underpass-dataset milestone is implied by this simulator-backed proof.

### Verified deployed state

Read-only stack inspection on 2026-10-11 confirmed:

- `hydrosense-data-dev` is `CREATE_COMPLETE` and contains only `hydrosense-readings-dev` and `hydrosense-incidents-dev`.
- `hydrosense-api-dev` is `UPDATE_COMPLETE` and runs the pre-hardening Lambda/API configuration with no reports-table or Cognito parameters.
- `hydrosense-frontend-dev` is `CREATE_COMPLETE` and serves the pre-integration build from private S3 through CloudFront OAC.
- API URL: `https://0795acig2g.execute-api.ap-south-1.amazonaws.com`.
- Dashboard URL: `https://d348efecbg3b7i.cloudfront.net`.
- A browser verification on 2026-10-11 loaded readings, incidents, and dashboard summary from the live API with HTTP 200 responses, no failed requests, and no console errors. It displayed the verified 25 cm simulated reading and its incident.
- The deployed underpass risk, hotspot, metric, event, and community-report routes all return HTTP 404 because that integration is not in the deployed Lambda build.
- `hydrosense-reports-dev` does not exist. The live Lambda role has no reports-table permission and remains limited to `DescribeTable`, `GetItem`, `PutItem`, `Scan`, and `UpdateItem` on the readings and incidents tables.
- The deployed API has only the unauthenticated `ANY /{proxy+}` route. No Cognito resources are present in the stack.

### Current template and code state

The current, undeployed templates add or change:

- A third DynamoDB table, `hydrosense-reports-dev`, with TTL cleanup on `expires_at`.
- DynamoDB transaction permission for atomic incident cooldown markers.
- Bounded scans, reading-age validation, bounded forecast caching, and `/ready` dependency checks.
- A Cognito operator user pool, no-secret SPA client, managed login domain, authorization-code + PKCE, required TOTP MFA, refresh rotation, and token revocation.
- API Gateway JWT authorization on exactly `POST /api/v1/readings`, `POST /api/v1/underpass/reports`, and `PATCH /api/v1/incidents/{incident_id}`. Read routes remain public.
- A production frontend build gate requiring the API URL and all three Cognito outputs.
- A private S3/CloudFront frontend with TLS-only bucket access and explicit API, Cognito, and OpenStreetMap CSP origins.
- An explicit `UNDERPASS_DATA_DIR` Lambda setting. Missing or malformed reviewed artifacts leave only the optional underpass module unavailable.

The current application tests and frontend build pass locally, but the undeployed templates have not received a fresh SAM build, SAM validation, or `cfn-lint` run. SAM CLI, `cfn-lint`, and `cfn-guard` are currently unavailable on this workstation, and the existing `.aws-sam/build` output is stale and unsafe to deploy. No change set has been created. The likely update is additive for the reports table and Cognito resources, plus in-place API, Lambda, IAM, and frontend changes; that must still be confirmed by reviewing CloudFormation change sets.

The templates remain development-oriented. Stateful resources use `DeletionPolicy: Delete` and `UpdateReplacePolicy: Delete`, DynamoDB point-in-time recovery is not configured, and logs retain only seven days. Those choices are explicit hackathon tradeoffs, not production retention policy.

### Compliance scan

CloudFormation Guard 3.2.1 was installed from the official Windows x86_64 release after verifying SHA-256 `52af28c02081f1067c6710c08619d359899734ec59d51f17f68e1b4b396a1203`. The AWS Guard Rules Registry was pinned to commit `7f7340c26ae5d5e8874651dbffeb12e0e9f505b6`, and its Well-Architected Security Pillar ruleset was run against all three templates.

The scan found these unresolved hardening items:

- Backend: the Lambda role uses inline policies; CloudWatch log groups do not use a customer-managed KMS key.
- Data: DynamoDB tables use encryption at rest but not customer-managed KMS keys.
- Frontend: the static asset bucket does not enable access logging or versioning.

No suppressions were added. These findings require an explicit cost, operations, and retention decision before calling the templates production-ready.

## Original cloud milestone

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
- One DynamoDB reports table: `hydrosense-reports-dev` in the current template.
- One application IAM principal or execution role restricted to those three tables.
- API Gateway HTTP API and one on-demand Python 3.12 Lambda function.
- CloudWatch access and function log groups with seven-day retention.

For hackathon-scale data, the first adapter may use bounded `Scan` operations to preserve the current repository interface. Add keys/indexes and purpose-specific query methods only after the cloud proof identifies a demonstrated need. Do not treat this as a production-scale design.

## Configuration

```text
STORAGE_BACKEND=json|dynamodb
AWS_REGION=ap-south-1
DYNAMODB_READINGS_TABLE=hydrosense-readings-dev
DYNAMODB_INCIDENTS_TABLE=hydrosense-incidents-dev
DYNAMODB_REPORTS_TABLE=hydrosense-reports-dev
DYNAMODB_MAX_SCAN_ITEMS=1000
UNDERPASS_DATA_DIR=/var/task/data/underpass
```

Use the standard AWS SDK credential provider chain. For local development, use an authenticated AWS profile or short-lived environment credentials supplied outside the repository. Do not add access keys, session tokens, phone numbers or certificates to `.env.example`, source code, logs or Git.

## Runtime IAM permissions

Restrict resources to the three exact table ARNs and allow only:

- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:UpdateItem`
- `dynamodb:Scan`
- `dynamodb:DescribeTable`
- `dynamodb:TransactWriteItems`

The runtime role must not create or delete tables. Provisioning credentials may separately manage resources during a controlled deployment or teardown. Bounded scans are acceptable for this small development dataset only; production scale requires query-oriented keys/indexes and cursor pagination.

## Reviewed release order (not executed)

No change set, deployment, asset upload, or cache invalidation has been run for this release. Before any mutation, create and inspect change sets in this order:

1. Data stack: add only the reports table and TTL configuration. Reject any change set that replaces or deletes the readings or incidents tables.
2. Backend stack: add reports permissions, Cognito resources, JWT route authorization, and the hardened Lambda package. Verify core read routes, protected mutation responses, `/ready`, and optional underpass HTTP 503 behavior before proceeding.
3. Frontend stack: pass the exact API origin and `https://<CognitoDomain output>` as `CognitoOrigin`; reject distribution or bucket replacement.
4. Frontend assets: build with the actual API and Cognito outputs, perform a local artifact review, then upload and invalidate CloudFront only after explicit approval.

The reviewed underpass artifacts are a separate prerequisite, not a deployment-generated dataset. Keep the module unavailable until those files have provenance and schema review. The existing readings, incidents, and summary paths are the rollback and smoke-test baseline at every stage.

### Proposed change sets

These names and actions are proposed only. No change set has been created.

1. `hydrosense-data-dev-release-20261011`: update `hydrosense-data-dev` from `infrastructure/dynamodb.yaml`, preserving `Environment=dev`, `ReadingsTableName=hydrosense-readings-dev`, and `IncidentsTableName=hydrosense-incidents-dev`, and setting `ReportsTableName=hydrosense-reports-dev`. The only accepted resource action is `Add ReportsTable`; reject replacement, removal, or modification of the two existing tables.
2. `hydrosense-api-dev-release-20261011`: create only after a fresh SAM container build and package inspection. Preserve the deployed frontend origin and existing table names; set the reports table and all bounded runtime parameters explicitly. Expected additions are the Cognito user pool, no-secret client, managed-login domain/branding, and SAM-generated permissions for the three protected mutation routes. Expected modifications are the Lambda package/configuration, runtime role policy, HTTP API authorization/CORS, and stage routes. Reject deletion or replacement of the API, function, log groups, or execution role unless separately reviewed.
3. `hydrosense-frontend-dev-release-20261011`: update `hydrosense-frontend-dev` with the deployed API origin and the new Cognito HTTPS origin. No resource addition, deletion, bucket replacement, or distribution replacement is expected; reject any such action. Publish assets and invalidate CloudFront only after this stack update and explicit approval.

The backend package gate is strict: its generated template must match the current source template; `app/services/underpass_risk.py` and all current routes must be present; `data/hydrosense.json`, caches, virtual environments, credentials, and unapproved underpass data must be absent; Linux-compatible dependencies and exact environment variables must be inspected before the backend change set is created.

### Security hardening assessment

- Replace the inline Lambda policies with a dedicated customer-managed policy only when its lifecycle and attachment are reviewed; keep the same exact table and log-group ARNs and action list. A managed policy improves governance but does not justify broader permissions.
- For a production retention decision, create a dedicated rotating KMS key with a scoped key policy, then apply it to DynamoDB and CloudWatch Logs. This adds key cost and operational dependencies and is not silently introduced into the development stack.
- Enable frontend bucket versioning before production publication. Add access logging only with a separate private encrypted log bucket and lifecycle policy; logging to the asset bucket itself is not acceptable.
- Revisit the development `Delete` retention policies, seven-day logs, DynamoDB point-in-time recovery, and alarms before claiming production readiness.

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
