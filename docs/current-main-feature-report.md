# HydroSense Current Main Feature Report

Report date: 2026-10-11
Baseline snapshot: `main` at merge commit `0319d7f`
Current status: production-readiness changes are present in the worktree and are not committed or deployed

## Executive summary

The merge retained the useful underpass-risk, community-report, dashboard, and AWS infrastructure work from commit `6c5f365`, while removing artifacts that made unavailable features appear operational.

Amazon Bedrock was not removed as a product feature. The fabricated Bedrock response generator was removed because it returned model names, confidence scores, visual findings, and estimated depths without making an AWS Bedrock request. The current code keeps nullable server-owned `image_url` and `ai_assessment` response fields for backward compatibility, but neither is accepted from report creation and the frontend does not render fabricated assessment output.

The currently hosted AWS application is still the pre-integration vertical slice. Browser verification on 2026-10-11 confirmed that its readings, incidents, and dashboard summary load from the live API and display correctly with no failed requests or console errors. The reports table, hardened backend, Cognito resources, merged dashboard, optional underpass module, and future Bedrock flow have not been deployed.

## Features currently on `main`

| Area | Status | Current behavior |
|---|---|---|
| FastAPI health and REST API | Implemented | Health, readings, incidents, dashboard summary, underpass, and community-report routes are defined. |
| Sensor ingestion | Implemented | Accepts ESP32-compatible or simulated water-level readings through a shared contract. |
| Water-level incident engine | Implemented | Rejects stale/future readings and uses a configurable threshold plus atomic cooldown-marker deduplication. |
| Incident operations | Implemented | Lists incidents, returns an individual incident, and validates lifecycle transitions. |
| Local persistence | Implemented | JSON-file repository is the local development default. Runtime files are excluded from Git. |
| DynamoDB persistence | Implemented in code | Readings, incidents, and community reports use the same storage protocol. |
| Community reports | Implemented in code | Creation requires a UUID, coordinates, hotspot, status, and optional notes. Identical UUID retries are idempotent; conflicting reuse returns 409. Images and AI claims are not accepted. |
| Report expiry | Implemented in code | DynamoDB records receive an `expires_at` TTL value; the API also filters expiry immediately. |
| Underpass risk service | Dataset-gated | Loads reviewed files when present and uses bounded live/cached/stale forecast states. Missing data or thresholds produce `unknown`, never zero-rain green. |
| Underpass API availability | Explicit | Risk, hotspot, metric, and event routes return HTTP `503` when the required reviewed dataset is absent. |
| React dashboard | Implemented | Provides overview, underpass map, telemetry desk, storm replay, incident controls, and field-report UI. |
| Honest unavailable states | Implemented | Core telemetry can load independently while the optional underpass module displays an unavailable notice. |
| Historical replay | Code ready, recovered data under review | The UI and API are present. The historical dataset has been recovered into a local branch, but it is not committed to the application or enabled at runtime pending provenance review. |
| Frontend map | Implemented | Leaflet and OpenStreetMap rendering are included when hotspot data is available. |
| Local simulator | Implemented | Sends clearly labelled simulated sensor readings through the real API contract. |
| Lambda/API Gateway | Deployed pre-merge | The FastAPI application is hosted through Mangum and API Gateway HTTP API. |
| Private S3/CloudFront frontend | Deployed pre-merge | Static files are served from a private S3 origin through CloudFront OAC and security headers. |
| Hosted mutation authentication | Template ready, not deployed | Cognito managed login uses authorization-code + PKCE and TOTP MFA; API Gateway JWT-protects POST/PATCH routes. |
| CloudWatch logs | Active | Lambda and API logs are retained for seven days. KMS CMKs and alarms are still deferred. |
| Reports DynamoDB table | Template ready, not deployed | CloudFormation defines an encrypted on-demand table keyed by `report_id` with TTL on `expires_at`. |
| Automated validation | Completed where tooling permits | Backend: 44 passed, including 25 focused underpass/report/persistence tests. Frontend typecheck and production build passed. CloudFormation service validation accepts all three current templates. SAM CLI, `cfn-lint`, and `cfn-guard` are unavailable, so the current source still requires fresh SAM packaging and local lint/compliance validation. |

CloudFormation Guard 3.2.1 also ran with the pinned AWS Well-Architected Security Pillar ruleset. It reported unresolved production hardening findings: an inline Lambda role policy, CloudWatch logs and DynamoDB without customer-managed KMS keys, and the frontend bucket without access logging or versioning. These are documented rather than suppressed.

The deployed optional routes (`/risk`, underpass hotspots/metrics/events/reports) return HTTP 404, the reports table is absent, and the live role has no reports permission. The live API is still unauthenticated; Cognito and JWT protection exist only in the current undeployed template.

Local browser verification at 390 x 844 and 1440 x 900 found no document-wide horizontal overflow. Core health, readiness, and dashboard summary requests returned HTTP 200; unavailable risk and historical-event requests returned HTTP 503, and the UI rendered no recovered 46-row or synthetic 200-row fallback. Forecast validation now requires 24 consecutive finite, nonnegative hourly and rolling rainfall values before assigning a tier. DynamoDB collision reads for idempotent report retries use strong consistency.

The existing `.aws-sam/build` directory is stale and must not be deployed. Its generated template does not match `infrastructure/backend.yaml`, its function artifact omits the current underpass service, and it contains ignored local runtime state at `data/hydrosense.json`. A fresh SAM build must be produced and inspected after the local-state packaging path is excluded. SAM CLI was not available during the recovery audit, so no replacement artifact was created.

## Underpass history recovery audit

The original feature commit is `6c5f365a488a4506d2a218040691978752df11a3`. Its `delhi-underpass-warning` entry was a gitlink to `ec5cb986fb88ce66c30a7da6714838fba4d70caf`, but the repository did not include a `.gitmodules` URL or the linked objects.

GitHub's exact-commit index identified that target in the public repository `MonalikaDoda/Underpass-Watch-Delhi`. The commit was fetched without checking it out and is preserved locally at:

- `recovery/underpass-dataset` -> `ec5cb986fb88ce66c30a7da6714838fba4d70caf`
- `recovery/hydrosense-feature` -> `6c5f365a488a4506d2a218040691978752df11a3`

No tracked file, index entry, current branch, or existing uncommitted change was replaced during recovery.

The recovered tree contains a standalone risk backend and React demo plus these data artifacts:

- `data/events.csv`: 46 rows, comprising 37 `flooded` and 9 `clear` outcomes across 16 hotspots and 15 storm days
- `data/hotspots.json`: 16 hotspot records
- `data/thresholds.json`: pooled thresholds and 16 hotspot entries
- `data/metrics.json`: 46 evaluation rows with counts consistent with `events.csv`
- `data/features.csv`: 46 derived rainfall-feature rows
- `data/loso_predictions.csv`, `data/rain/hourly.csv`, and `SOURCES.md`: evaluation, source-rainfall, and provenance material

All four required artifacts and optional `features.csv` pass the current Pydantic contracts and loader-equivalent CSV/JSON checks. A separate cross-file audit found unique event and hotspot IDs, valid ISO dates and coordinate ranges, complete event-to-hotspot and threshold coverage, no duplicate `(date, hotspot, outcome)` facts, 25 syntactically valid HTTPS source URLs represented in `SOURCES.md`, and matching event identities across features and predictions. Blank values occur only in optional narrative fields such as notes, source-reported rainfall, and event time text.

The recovered calculation was also independently reproduced from `data/rain/hourly.csv` using its documented 36-hour windows and quartile rules. All 46 feature rows, all pooled and per-hotspot thresholds, all 46 leave-one-storm-out predictions, every per-storm-day confusion count, and the aggregate metrics matched the committed outputs. The per-hotspot evaluation reports 27 of 37 floods caught, 10 missed, 6 false alarms, and 3 of 9 clear cases correctly classified. This establishes internal consistency and format compatibility, not factual verification or production suitability.

The upstream documentation links every event to a public article and attributes rainfall to Open-Meteo under CC BY 4.0. The audit verified link syntax and cross-references, not the factual content of all 25 articles. The documentation also states that hotspot coordinates are assistant estimates that were not map-checked, news coverage is incomplete, clear cases are sparse, infrastructure changes affect behavior, and the effective evaluation sample is only 15 storm days. For that reason, the recovered files have not been copied into `backend/data/underpass` and the optional module remains unavailable by design.

The safest eventual integration is data-only: independently review event attribution and coordinates, retain `SOURCES.md` and the Open-Meteo attribution, then install only `hotspots.json`, `thresholds.json`, `metrics.json`, `events.csv`, and optionally `features.csv` under `backend/data/underpass`. The standalone backend, standalone web app, `mock-risk.json`, and no-threshold zero-risk behavior must not be restored.

## What was removed during the merge

| Removed artifact or behavior | Reason |
|---|---|
| `frontend/src/api/mockData.ts` | It supplied fabricated hotspots, events, metrics, reports, and model output whenever a real API call failed. |
| Silent mock fallbacks in `frontend/src/api/client.ts` | API failures must remain visible; network or backend failure must not look like successful live data. |
| Synthetic Bedrock assessment generation in the backend | It claimed an Anthropic model, Bedrock provider, confidence, evidence, and estimated depth without invoking Bedrock. |
| Synthetic Bedrock assessment generation in the frontend | It produced the same false-success behavior when report submission failed. |
| Client-provided `ai_assessment` in `CommunityReportCreate` | A browser must not be allowed to assert that output came from a trusted model. The field is server-owned. |
| Broken `delhi-underpass-warning` gitlink integration | It had no `.gitmodules` entry and its directory was empty. The target was later recovered from its public source into a local recovery branch, but the gitlink itself remains unsuitable for application packaging. |
| Root `data/hydrosense.json` | It was committed runtime state containing report UUIDs and timestamps, not source data. Root `/data/` is now ignored. |
| `scripts/generate_synthetic_dataset.py` | It depended on missing base hotspot, event, and rainfall files and could not reproduce the claimed dataset. |
| Hardcoded 200-record, 21-day, and evaluation-score claims | Those inputs and results were not present in the repository. Metrics now appear only when a reviewed dataset is installed. |
| Fabricated default `16.4 cm` sensor value | The dashboard now displays `--` when no real or clearly simulated reading is available. |
| Claims that physical hardware and image AI were live | Hardware remains simulator-backed, and image analysis remains planned until verified. |

## What remains for the Bedrock feature

The following extension points remain intentionally:

- `CommunityReport.ai_assessment` is nullable in backend and frontend response contracts.
- `CommunityReport.image_url` is a nullable legacy response field.
- The project summary describes Bedrock photo assessment as proposed work with human-review safeguards.

There is no current report upload endpoint, image submission field, Bedrock invocation, or model-output display.

## Bedrock integration design

### Required architecture

1. The browser requests a short-lived presigned upload URL from the backend.
2. The browser uploads the image directly to a private, encrypted S3 evidence prefix.
3. The browser submits the community report with an S3 object key, never a base64 image or client-generated AI result.
4. The backend stores the report with `analysis_status: pending`.
5. A server-side analyzer loads the object, invokes an image-capable Amazon Bedrock model through the Bedrock Runtime Converse API, validates the structured response, and updates the report.
6. The frontend refreshes or polls the report and displays `pending`, `completed`, `failed`, or `human_review_required` without inventing fallback output.

A DynamoDB Stream-triggered analyzer Lambda is the recommended shape for this project because report submission remains fast and model latency does not block API Gateway. A synchronous first proof is acceptable only if measured invocation latency stays within the configured Lambda and API timeouts.

### Model invocation requirements

- Discover available image-capable models at deployment time with the Bedrock control-plane API in the selected region; do not hardcode an unverified model ID.
- Use `bedrock-runtime` and the Converse API for the Python backend.
- Configure `maxTokens` explicitly on every invocation.
- Keep the model or inference-profile ID in environment configuration.
- Validate model output against a strict Pydantic schema before persistence.
- Record model ID, invocation timestamp, model request ID, analysis status, and a prompt/schema version.
- Never treat model output as an official safety determination or exact measured water depth.

### Suggested assessment contract

```json
{
  "analysis_status": "completed",
  "visible_waterlogging": "likely",
  "visual_evidence": ["standing water visible across part of the carriageway"],
  "limitations": ["unknown camera height", "no calibrated depth marker"],
  "needs_human_review": true,
  "model_id": "configured-server-side",
  "analyzed_at": "2026-10-11T12:00:00Z",
  "schema_version": "1"
}
```

Confidence scores and numeric water-depth estimates should not be exposed until a labelled evaluation demonstrates that they are meaningful.

### Security and storage requirements

- Store images in private S3, not DynamoDB. DynamoDB items have a 400 KB limit, while the current browser preview can create multi-megabyte data URLs.
- Permit only expected JPEG, PNG, or WebP content types and enforce a small upload limit.
- Use short-lived presigned URLs and random object keys; do not accept arbitrary S3 URLs from the client.
- Scope the analyzer role to `bedrock:InvokeModel` for the selected model or inference profile, `s3:GetObject` for the evidence prefix, and update access to the reports table.
- Do not grant Bedrock permissions to the browser or expose AWS credentials.
- Avoid logging image bytes, report notes, or model prompts containing personal information.
- Keep CloudTrail enabled and use bounded CloudWatch retention.

## Bedrock implementation work plan

1. Verify AWS CLI v2 credentials and discover image-capable Bedrock models available to `hydrosense-dev` in the target region.
2. Add configuration for the model ID, evidence bucket, upload limits, and analysis enablement.
3. Add `analysis_status`, validated assessment fields, S3 object key, and analysis metadata to the contracts and repository tests.
4. Add a private evidence bucket, CORS rules for the CloudFront origin, and least-privilege upload/read policies.
5. Add a presigned-upload endpoint and reject base64/data-URL report images.
6. Implement a `BedrockImageAssessmentService` using an injectable Bedrock Runtime client and Converse API.
7. Add the analyzer Lambda and DynamoDB Stream trigger, or measure and document a bounded synchronous proof.
8. Add unit tests with a fake Bedrock client plus one opt-in AWS integration test that performs a real invocation.
9. Update the frontend with pending, failed, completed, and human-review states.
10. Deploy the reports table and backend changes, run one traceable report end to end, and retain sanitized CloudWatch and DynamoDB evidence.

## Other planned integrations

These were not removed and remain separate milestones:

- SNS notification delivery after recipient and sandbox constraints are resolved.
- CloudWatch alarms for Lambda errors, throttles, API 5xx responses, and Bedrock analyzer failures.
- AWS IoT Core MQTT after the physical ESP32 sensor is wired, calibrated, and locally validated.
- A reviewed, attributable underpass event/threshold dataset.

## Immediate deployment gap

Before presenting the revised application as live, review CloudFormation change sets, then deploy and verify the reports table, Cognito resources, updated API stack, and rebuilt frontend. Create an operator, complete managed-login/TOTP enrollment, verify public reads and authorized mutations, and test `/ready`. Bedrock remains planned until a real invocation has been observed and its output has passed schema validation.
