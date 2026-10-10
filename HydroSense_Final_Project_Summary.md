# HydroSense --- Final Project Summary and Implementation Brief

**Project:** HydroSense\
**Focus:** Water-risk intelligence for urban environments, with an
initial focus on Delhi underpasses\
**Document purpose:** A consolidated project brief for the repository's
`docs/` directory, team alignment, implementation, and hackathon
judging.

> **Status discipline:** This document distinguishes existing/reported
> work from planned work. Do not present a planned feature, AWS service,
> or AI capability as implemented until it has been built and tested.

------------------------------------------------------------------------

## 1. Executive Summary

HydroSense is a water-risk monitoring and decision-support platform that
brings together:

1.  **Urban Flood Intelligence** --- forecast-based risk estimates for
    Delhi underpass hotspots, historical evaluation, and community
    reports about current road conditions.
2.  **Water Infrastructure Monitoring** --- an ESP32-based water-level
    prototype and simulated pipeline pressure/flow anomaly detection.

A selected AI extension is **AI Visual Assessment of Community Flood
Reports**. When a user submits a photo for an underpass, a
vision-capable model can assess whether visible waterlogging appears in
the image and return structured findings with uncertainty. HydroSense
then presents that assessment separately from the forecast risk and the
user's report. It must not treat an image as proof that a road is safe
or infer water depth or hidden hazards from a photo.

The goal is to make fragmented water-risk information easier to
understand and act on, while communicating uncertainty and limitations
honestly. HydroSense is a prototype decision-support system, not an
official emergency warning or road-closure service.

## 2. Problem

Heavy rainfall can cause waterlogging at underpasses, while changes in
water level and pipeline leaks create other water-management challenges.
People may not have a single view that combines forecast risk,
historical evidence, local observations, and water-level monitoring.

HydroSense aims to provide one dashboard where users can: - See
estimated flood risk for selected underpasses. - Understand the evidence
behind a risk flag. - Submit and review ground-level reports. - Review
historical storm outcomes against risk estimates. - Monitor a controlled
water-level prototype. - Demonstrate how unusual pipeline pressure/flow
readings could generate an incident.

## 3. Product Scope

### Module A --- Urban Flood Intelligence

#### A1. Underpass risk estimates

-   Initial coverage: 16 Delhi underpass hotspots.
-   Inputs: weather forecast/rainfall data and a historical incident
    dataset.
-   Current described method: location-specific rainfall thresholds
    informed by historical incidents, with shared thresholds for
    locations that have fewer than three recorded floods; these should
    be labelled as limited evidence.
-   Outputs: colour-coded risk estimate, risk window where supported by
    the existing service, and a "Why this alert?" explanation.
-   The existing risk service is described as using Open-Meteo forecast
    data, with the default ECMWF IFS model retained for both historical
    rainfall retrieval and live forecast use.
-   The current approach is rule/threshold-based. It is **not a trained
    machine-learning flood-prediction model**.

#### A2. Community flood reports

Users can submit one of: - Flooded - Passable - Not flooded

A report should include at least: - Hotspot identifier - Report status -
Timestamp - Optional image - A stable report identifier

The interface should show report freshness and conflicts. A report is an
observation submitted by a user, not necessarily a verified fact.

If reports are intended to remain active for approximately 45 minutes: -
The API must filter expired reports by timestamp immediately. - DynamoDB
TTL may be used for eventual cleanup, but TTL deletion is asynchronous
and must not be relied on for exact 45-minute expiry. - Add rate
limiting and appropriate input validation. - If identity/authentication
is not implemented, state that reports are unverified and potentially
vulnerable to abuse.

#### A3. Historical storm replay and evaluation

-   Replay a past storm and compare model outputs with recorded
    outcomes.
-   Show evaluation metrics and caveats directly in the interface.
-   Clearly distinguish recorded observations from predicted/estimated
    risk.

### Module B --- Water Infrastructure Monitoring

#### B1. ESP32 water-level prototype

-   Hardware: ESP32, HC-SR04 ultrasonic sensor, and OLED display.
-   Purpose: measure water level in a controlled container and show
    `NORMAL`, `CAUTION`, or `HIGH`.
-   This prototype does not measure the water depth of a real Delhi road
    or underpass.
-   Indicative pins from the current project context: TRIG GPIO5, ECHO
    GPIO18 through a voltage divider/level shifter, OLED SDA GPIO21 and
    SCL GPIO22. Confirm actual board and module wiring before use.
-   HC-SR04 Echo may output 5 V, while ESP32 GPIO is 3.3 V tolerant. Use
    a suitable divider/level shifter and keep electronics dry.
-   Example calculation:
    `water_depth_cm = configured_reference_depth_cm - measured_distance_cm`.
-   Thresholds are demo values until calibrated and validated.

#### B2. Pipeline leak demonstration

-   Current described implementation uses simulated pressure/flow
    readings.
-   Rules can identify unusual values and create a potential leak
    incident.
-   Do not claim live municipal pipeline monitoring or verified
    real-world leak detection.

## 4. Selected AI Use Case --- AI Visual Assessment of Community Flood Reports

### Why this AI feature?

The existing threshold-based risk engine can estimate risk from rainfall
and historical evidence, but it cannot inspect a newly submitted
photograph. A vision-capable model can perform a distinct inference
task: assess visible image evidence for apparent waterlogging.

This is a stronger and more defensible AI use case than asking a
language model to merely rephrase an existing threshold alert.

### Proposed user flow

1.  A user selects an underpass and submits a photo with a community
    status.
2.  The backend validates the image and report metadata.
3.  A multimodal, vision-capable foundation model is invoked through
    Amazon Bedrock, if the selected model is available in the chosen
    region.
4.  The model returns a constrained structured assessment, such as:
    -   `visible_waterlogging`: `likely`, `not_obvious`, or `uncertain`
    -   `visual_evidence`: brief description of visible evidence
    -   `limitations`: e.g., view obstructed, image dark, camera angle
        insufficient
    -   `needs_human_review`: boolean
5.  The backend stores the AI assessment separately from the user's own
    status and the forecast-based risk.
6.  The dashboard displays all three separately and flags disagreement
    for review.

### Example

-   Forecast-based risk: High
-   User report: Passable
-   Photo assessment: Visible waterlogging likely
-   Combined display: Conflicting evidence --- review current conditions

The system must not automatically claim the road is safe, infer water
depth, identify hidden hazards, or silently overrule a user report. A
photo may be old, misleading, obstructed, or taken from an
unrepresentative angle.

### Evaluation and safeguards

-   Build a small, manually labelled test set of underpass/road images
    before claiming performance.
-   Include dry roads, visible waterlogging, reflections,
    nighttime/low-light images, obstructed views, and ambiguous cases
    where possible.
-   Measure performance against human-reviewed labels; report false
    positives, false negatives, and uncertain/abstained cases.
-   Keep the AI assessment experimental until it has been evaluated.
-   Use structured output and validate it on the backend.
-   Limit image size and accepted formats; avoid storing unnecessary
    personal information.
-   If the model fails or returns malformed output, fall back to the
    user's report and existing forecast-risk result.
-   The AI feature is **planned until implemented and tested**. Do not
    claim it is already live.

### What AI is and is not in this project

-   Current flood risk: historical thresholds and forecast data; not
    trained ML.
-   Current sensor status: sensor measurements plus threshold rules.
-   Current simulated leak detection: rule-based anomaly checks on
    simulated readings.
-   Proposed AI: vision-model assessment of submitted photos, through
    Amazon Bedrock.
-   Community reports: user submissions, not AI-generated evidence.

## 5. Dataset and Existing Evaluation

The underpass project context reports: - 46 historical records: 37 flood
records and 9 "stayed clear" records. - 15 storm days spanning
2020--2026. - 16 underpass hotspots. - Each historical incident row has
a news/source link. - Data files include `data/events.csv` and
`SOURCES.md`. - Hourly rainfall was downloaded from Open-Meteo for each
hotspot/date. - The default ECMWF IFS model was retained to match the
live forecast source. - For hotspots with fewer than three recorded
floods, a shared threshold is used and the location should be labelled
"limited evidence".

Reported hold-one-storm-day-out results supplied by the project team: -
27 of 37 recorded floods detected. - 10 of 37 recorded floods missed. -
6 of 9 recorded clear cases incorrectly warned.

Derived descriptive metrics: - Flood detection rate/recall on the
recorded flood rows: 27/37 = 73.0%. - Miss rate on the recorded flood
rows: 10/37 = 27.0%. - False-warning rate on recorded clear rows: 6/9 =
66.7%.

These are the team's reported results and have not been independently
revalidated in this document. The dataset is small, the clear subset
contains only nine records, and hourly rainfall may be too coarse to
distinguish conditions between underpasses during the same storm. These
results should not be presented as evidence of reliable citywide
prediction.

## 6. Intended Architecture

``` text
React / Vite dashboard
        |
        v
FastAPI backend
  |          |             |
  |          |             +--> Vision assessment via Amazon Bedrock (planned)
  |          |
  |          +--> Underpass risk module
  |               - forecast + historical thresholds
  |               - risk explanation
  |               - historical replay/evaluation
  |
  +--> Water monitoring APIs
       - ESP32 readings or simulator
       - simulated leak readings
       - incident creation
        |
        v
Persistence adapter
  |                     |
  +--> Local JSON       +--> Amazon DynamoDB (planned cloud adapter)
                              |
                              +--> readings
                              +--> incidents
                              +--> community reports / AI assessment metadata
```

### Integration recommendation

Integrate the existing underpass `backend/risk/` module into the
existing FastAPI backend if dependency compatibility allows. Reuse its
dataset, source links, thresholds, service logic, and tests. Avoid
creating a second independently deployed API unless the existing code
cannot be consolidated safely.

Keep the data source explicit in the API/UI, for example: -
`simulated_sensor` - `esp32` - `simulated_leak` - `historical_dataset` -
`forecast` - `operator_report` - `community_report` -
`ai_image_assessment`

## 7. AWS Services and Their Roles

The following is the recommended target architecture. Mark each service
as deployed only after it is actually configured and tested.

  -----------------------------------------------------------------------
  AWS service             Intended purpose        Verification required
  ----------------------- ----------------------- -----------------------
  AWS Amplify Hosting     Host the React/Vite     Open the deployed URL
                          frontend and provide a  and verify the current
                          public URL              frontend build

  AWS App Runner          Run the existing        Check service health
                          FastAPI backend         and exercise real API
                                                  endpoints

  Amazon DynamoDB         Persist readings,       Write a record, read it
                          incidents, community    back, restart/redeploy
                          reports, and relevant   the backend, and verify
                          AI assessment metadata  persistence

  Amazon CloudWatch       Collect backend/service Show current logs for a
                          logs and aid            real request
                          troubleshooting         

  Amazon Bedrock          Invoke a selected       Confirm model/region
                          vision-capable          access and demonstrate
                          foundation model for    a tested image
                          the proposed photo      request/response
                          assessment              

  AWS IoT Core (optional  Secure MQTT             Claim only after device
  future work)            connectivity for ESP32  authentication and
                          telemetry               message flow are
                                                  implemented and tested

  AWS Budgets             Alert on spending       Verify the budget and
  (recommended account    against a configured    notification settings
  safety)                 budget                  in the account
  -----------------------------------------------------------------------

Suggested initial region from the project plan: `ap-south-1` (Mumbai),
subject to confirming availability of the required services and model
access. The project team has an AWS account with \$100 in credits
according to the project context; confirm credit expiry and billing
status before deploying.

Security and cost controls: - Use least-privilege IAM roles. - Do not
hardcode AWS credentials or commit secrets. - Prefer the AWS SDK
credential provider chain and service roles. - Use on-demand DynamoDB
capacity for a small prototype unless measured usage justifies another
choice. - Set a budget alert, but remember that a budget alert is not a
hard spending cap. - Keep logs free of unnecessary personal or sensitive
data. - Validate and rate-limit public report endpoints.

## 8. Current Project State --- Based on the Available Project Context

### Reported as existing/working locally

-   React/Vite frontend and FastAPI backend scaffold.
-   Shared API contracts for sensor readings, leak measurements,
    incidents, and dashboard summary.
-   `/health` endpoint and API documentation.
-   Local JSON persistence and simulator-to-FastAPI-to-dashboard
    vertical slice.
-   Backend tests were reported passing (the latest stated report was 14
    passing tests).
-   Frontend type-check and production build were reported passing.
-   Underpass risk service in `backend/risk/`, historical dataset/source
    references, and risk tests were reported as existing; 7 risk tests
    were reported passing.
-   A dry October forecast test reportedly showed all 16 hotspots green.
-   A simulated water-level reading crossing a configured threshold
    reportedly created a high-water incident.

These statements are based on project-context reports, not a fresh run
of the repository in this document.

### Not confirmed as completed

-   AWS persistence and deployment.
-   A verified public production URL.
-   End-to-end DynamoDB read/write and persistence after restart.
-   Physical ESP32-to-cloud connectivity.
-   Live municipal sensor integration.
-   The proposed Amazon Bedrock photo-assessment feature.
-   A labelled photo evaluation set and measured AI performance.
-   Production-grade authentication/moderation for community reports.

## 9. Recommended Implementation Order

1.  Inspect the current repository, `PROJECT_CONTEXT.md`,
    `backend/risk/`, risk tests, and HydroSense API contracts.
2.  Write an integration plan before changing code; preserve existing
    tests and risk logic.
3.  Integrate the underpass module into the shared FastAPI backend and
    connect the 16-hotspot map to its APIs.
4.  Add community reporting with timestamps, input validation, conflict
    display, rate limiting, and server-side expiry filtering.
5.  Add historical storm replay and an evaluation panel that uses the
    actual evaluation output.
6.  Deploy the existing application path to AWS: Amplify frontend, App
    Runner backend, DynamoDB persistence, CloudWatch logs.
7.  Verify a real cloud write/read path and persistent storage after
    backend restart.
8.  Build a small labelled photo dataset and implement the Bedrock
    visual assessment behind a feature flag.
9.  Evaluate image-assessment outputs and failure modes; show uncertain
    cases and never use AI alone to declare a road safe.
10. Test the ESP32 locally; only then consider IoT Core integration.
11. Prepare a short demo, architecture diagram, README, source/data
    credits, and explicit limitations.

Do not block the main software path on hardware availability; keep the
simulator available as a clearly labelled fallback.

## 10. Demo Flow

Recommended judge demo: 1. Replay a historical storm and show recorded
outcomes versus risk estimates. 2. Select an underpass and explain its
risk window, evidence quality, and "Why this alert?" text. 3. Submit a
community report and show how the interface handles fresh, stale, or
conflicting observations. 4. If the Bedrock feature is implemented,
upload a test photo and show its structured visual assessment separately
from forecast risk and user status. 5. Demonstrate the controlled ESP32
water-level prototype or clearly labelled simulator. 6. Show the actual
deployed AWS application, a persisted DynamoDB record, and CloudWatch
logs if the cloud path has been verified.

## 11. Judge Pitch

Good morning, judges.

HydroSense is a water-risk monitoring and decision-support platform
focused on helping people understand water-related risks more clearly.

Our Urban Flood Intelligence module estimates risk across 16 Delhi
underpass hotspots using weather forecasts and historical incidents. It
displays risk levels, explains why a location is flagged, and supports
community reports about current road conditions. We are also developing
an AI visual-assessment feature that examines submitted road photos for
visible signs of waterlogging and flags cases where visual evidence
conflicts with the forecast or community reports.

Our second module demonstrates water infrastructure monitoring through
an ESP32 ultrasonic water-level prototype and simulated pipeline
pressure/flow anomaly detection.

The platform uses a shared backend and is designed for AWS-hosted
delivery and persistent cloud storage. We are careful to distinguish
real observations, user reports, simulated readings, modelled risk, and
AI assessments.

Our existing flood-risk logic is threshold-based, not a trained ML
predictor, and our historical evaluation is small. We present HydroSense
as a decision-support prototype, not an official warning system. Our
goal is to combine evidence sources responsibly and help users identify
where further attention may be needed.

Thank you.

## 12. Claims We Must Not Make Without Evidence

Do not claim: - "Our AI predicts floods" unless a trained and evaluated
predictive model actually exists. - "Our AI verifies a road is safe" ---
photo assessment cannot establish safety. - "Real-time municipal
pipeline monitoring" while readings are simulated. - "Live ESP32-to-AWS
telemetry" before the connection is implemented and verified. - "AWS
deployed" before a public deployment and backend health check are
confirmed. - "Community reports are verified" without an actual
verification process. - "73% accurate" based only on the 27/37
flood-detection count. That is a detection rate on the reported flood
subset, not overall accuracy. - "AI visual assessment is live" until the
Bedrock call, UI flow, error handling, and evaluation have been tested.

## 13. Team Responsibilities

Suggested ownership based on the current team plan: - **Mukul:**
FastAPI/backend integration, AWS deployment, API contracts, persistence,
and end-to-end verification. - **Rasleen:** ESP32 + HC-SR04 + OLED
prototype, local calibration, electrical safety, and a sample payload
matching the API schema. - **Poojya:** Dashboard/map, underpass details,
report interaction, visual status/conflict display, and evaluation UI.

Team members should coordinate API contracts before integrating modules.
Keep the simulator working as a fallback while the hardware and cloud
paths are developed.

------------------------------------------------------------------------

**One-line description:** HydroSense combines forecast-based underpass
risk estimates, community flood observations, experimental AI assessment
of submitted road photos, and a water-level/leak-monitoring prototype in
one transparent water-risk decision-support platform.
