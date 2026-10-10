# Minimal AWS Integration Plan

## Status

AWS persistence is **planned, not implemented or verified**. Local JSON remains the default development backend until the cloud verification test below passes. No hardware or AWS IoT milestone is implied by simulator success.

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
- CloudWatch logs only when the backend is deployed to an AWS compute service; local verification uses normal application logs.

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

## Later, separately verified steps

- AWS IoT Core MQTT for the physical ESP32 after Rasleen completes local wiring and calibration.
- SNS alert delivery after sandbox/recipient constraints are resolved.
- S3 only for real source datasets or analysis artifacts that the demo actually uses.
- Deployment compute and API Gateway only after the local FastAPI workflow remains stable.
