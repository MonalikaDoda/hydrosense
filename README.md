# HydroSense

HydroSense is a Delhi-focused decision-support prototype for flood risk, simulated water-loss anomalies, and equity-aware incident prioritization. The current vertical slice processes simulated water-level readings into persisted incidents and displays them in the dashboard.

Synthetic readings and demo locations must remain clearly labelled. The project does not claim citywide flood prediction, exact underground leak localization, or access to live municipal sensor data.

## Implemented vertical slice

- FastAPI reading ingestion, latest readings, incident list/detail, status updates, and dashboard summary
- Configurable 24 cm default threshold and five-minute duplicate suppression
- JSON-file local persistence and verified DynamoDB persistence behind a replaceable repository interface
- FastAPI deployed to AWS Lambda behind API Gateway HTTP API
- Least-privilege Lambda role, API access logs, and seven-day log retention
- Cognito managed login using authorization-code + PKCE for state-changing hosted routes
- ESP32-compatible Python simulator
- Responsive React dashboard with live API data and loading, failure, and empty states
- Dataset-gated underpass risk, map, evaluation, and replay modules with explicit HTTP 503 unavailable states
- Community field reports with JSON/DynamoDB persistence and a 45-minute active window
- CloudFormation definitions for the reports table and its TTL policy
- Strict Pydantic v2 and matching TypeScript contracts

The current code and templates are ahead of the hosted application. The deployed stacks still run the pre-integration vertical slice with two DynamoDB tables and no Cognito resources. The reports table, hardened backend, Cognito-protected mutations, and revised dashboard have not been deployed. Amazon Bedrock image assessment, AWS IoT, SNS alerts, CloudWatch alarms, physical hardware validation, a reviewed underpass dataset, and leak anomaly processing are not implemented.

## Prerequisites

- Python 3.12+
- Node.js 20+ and npm

## Run the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health`, dependency readiness at `http://127.0.0.1:8000/ready`, or Swagger UI at `http://127.0.0.1:8000/docs`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The backend must be running for its health indicator.

## Run the vertical slice

With backend and frontend running in separate terminals, send an above-threshold reading:

```powershell
py scripts\simulate_sensor.py --depth-cm 26
```

Refresh the dashboard to see the simulated reading and generated incident. Local records are stored in `backend/data/hydrosense.json` and excluded from Git. Set `STORAGE_PATH`, `WATER_ALERT_THRESHOLD_CM`, and `ALERT_COOLDOWN_SECONDS` in a local `.env` to override defaults.

## Run checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

cd ..\frontend
npm run typecheck
npm run build
```

Configuration placeholders are documented in `.env.example`. Copy values into a local `.env`; never commit secrets, certificates, private keys, or real phone numbers.

Local development does not configure Cognito, so local FastAPI mutations remain available. In the hosted design, API Gateway requires a valid Cognito access token for reading ingestion, community-report submission, and incident status updates. Read routes remain public.

The underpass module becomes available only when `UNDERPASS_DATA_DIR` identifies a reviewed directory containing valid, nonempty `hotspots.json`, `thresholds.json`, `metrics.json`, and `events.csv` artifacts. `features.csv` is optional. No reviewed dataset is currently committed, so the map, metrics, and replay views truthfully remain unavailable; community reports and core telemetry continue to operate independently.

## Deploy the AWS backend

The deployed stacks use `ap-south-1`, the `hydrosense-dev` SSO profile, and the templates under `infrastructure/`. AWS SAM CLI and Docker are required for the backend package.

```powershell
aws cloudformation deploy `
	--template-file infrastructure\dynamodb.yaml `
	--stack-name hydrosense-data-dev `
	--region ap-south-1 `
	--profile hydrosense-dev

sam build --use-container --template-file infrastructure\backend.yaml
sam deploy `
	--stack-name hydrosense-api-dev `
	--resolve-s3 `
	--capabilities CAPABILITY_IAM `
	--region ap-south-1 `
	--profile hydrosense-dev `
	--parameter-overrides FrontendOrigin=http://localhost:5173
```

For a new environment, the localhost callback is temporary: deploy the frontend infrastructure after obtaining `ApiUrl`, then update the API stack with its `FrontendOrigin` set to the `FrontendUrl`. This makes the final CORS, Cognito callback, and logout URLs exact.

Retrieve the current API URL without hardcoding it:

```powershell
$apiUrl = aws cloudformation describe-stacks `
	--stack-name hydrosense-api-dev `
	--region ap-south-1 `
	--profile hydrosense-dev `
	--query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
	--output text
```

Retrieve the Cognito domain output and form its HTTPS origin before updating the frontend stack:

```powershell
$cognitoDomain = aws cloudformation describe-stacks --stack-name hydrosense-api-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='CognitoDomain'].OutputValue" --output text
$cognitoOrigin = "https://$cognitoDomain"
```

Deploy and publish the frontend after the backend URL is available:

```powershell
aws cloudformation deploy `
	--template-file infrastructure\frontend.yaml `
	--stack-name hydrosense-frontend-dev `
	--region ap-south-1 `
	--profile hydrosense-dev `
	--parameter-overrides ApiOrigin=$apiUrl CognitoOrigin=$cognitoOrigin

$userPoolId = aws cloudformation describe-stacks --stack-name hydrosense-api-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" --output text
$userPoolClientId = aws cloudformation describe-stacks --stack-name hydrosense-api-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolClientId'].OutputValue" --output text
$env:VITE_API_BASE_URL=$apiUrl
$env:VITE_COGNITO_USER_POOL_ID=$userPoolId
$env:VITE_COGNITO_USER_POOL_CLIENT_ID=$userPoolClientId
$env:VITE_COGNITO_DOMAIN=$cognitoDomain
npm --prefix frontend run build

$bucket = aws cloudformation describe-stacks --stack-name hydrosense-frontend-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text
$distribution = aws cloudformation describe-stacks --stack-name hydrosense-frontend-dev --region ap-south-1 --profile hydrosense-dev --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" --output text
aws s3 sync frontend\dist "s3://$bucket" --delete --region ap-south-1 --profile hydrosense-dev
aws cloudfront create-invalidation --distribution-id $distribution --paths "/*" --profile hydrosense-dev
```

Create operators administratively; public self-sign-up is disabled. The first sign-in requires the temporary password and TOTP enrollment:

```powershell
aws cognito-idp admin-create-user `
	--user-pool-id "<CognitoUserPoolId output>" `
	--username "operator@example.com" `
	--user-attributes Name=email,Value=operator@example.com Name=email_verified,Value=true `
	--region ap-south-1 `
	--profile hydrosense-dev
```

No deployment or CloudFormation change set was created for the current hardening and Cognito changes.

## Documentation

- [Project specification](docs/HydroSense_Project_Specification_for_IDE.md)
- [API contract](docs/api-contract.md)
- [Minimal AWS integration plan](docs/aws-integration-plan.md)
- [Current main feature and merge report](docs/current-main-feature-report.md)
- [Sprint 0 checklist](docs/sprint-0-checklist.md)
- [Hardware handoff](hardware/README.md)
