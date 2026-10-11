"""Evidence image storage and Bedrock advisory assessment for community reports.

Security rules enforced here:
- Clients never receive S3 credentials. They receive a short-lived presigned POST
  scoped to one object key, one content type, and a byte-size ceiling.
- Clients never supply a raw S3 URL or key for assessment without it first being
  validated to belong to the report it claims to describe.
- Image bytes and any model output are never written to logs.
- The model is instructed to stay advisory; output is rejected if it asserts
  certainty, an exact depth, or that a route is safe.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from app.config import Settings

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_FORBIDDEN_PHRASES = (
    "safe to pass",
    "safe to cross",
    "is safe",
    "guaranteed",
    "exact depth",
    "exactly",
    "certainly flooded",
    "definitely flooded",
    "100%",
    "no risk",
)

ASSESSMENT_DISCLAIMER = (
    "Automated advisory read of a single community-submitted photo. Not a depth "
    "measurement, not a safety certification. Follow official guidance."
)

_SYSTEM_PROMPT = (
    "You are an advisory assistant reviewing one photo submitted by a member of "
    "the public reporting possible urban waterlogging. Describe only what is "
    "visibly observable (presence of standing water, approximate relative "
    "extent, visible hazards such as submerged vehicles or debris). "
    "You must never state an exact water depth, never claim a route is safe or "
    "unsafe with certainty, and never claim complete certainty of flooding. "
    "If the image is unclear, unrelated to water, or inconclusive, say so "
    "plainly. Respond in 2-3 short sentences of plain advisory text only."
)


class EvidenceStorageError(RuntimeError):
    """Raised when the evidence bucket is not configured or an S3 call fails."""


class BedrockAssessmentError(RuntimeError):
    """Raised when the model cannot be invoked or its output fails validation."""


class S3Client(Protocol):
    def generate_presigned_post(self, **kwargs: Any) -> dict[str, Any]: ...

    def head_object(self, **kwargs: Any) -> dict[str, Any]: ...

    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...


class BedrockRuntimeClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


class EvidenceStorageService:
    def __init__(self, settings: Settings, s3_client: S3Client | None = None) -> None:
        self.settings = settings
        self._client = s3_client

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.evidence_bucket_name)

    def _require_client(self) -> S3Client:
        if not self.is_configured:
            raise EvidenceStorageError("Image evidence storage is not configured on this deployment.")
        if self._client is None:
            import boto3

            region = self.settings.aws_region
            self._client = boto3.client(
                "s3",
                region_name=region,
                endpoint_url=f"https://s3.{region}.amazonaws.com",
            )
        return self._client

    def build_key(self, report_id: str, content_type: str) -> str:
        extension = _CONTENT_TYPE_EXTENSIONS[content_type]
        return f"reports/{report_id}/{uuid.uuid4()}.{extension}"

    def create_upload_post(self, report_id: str, content_type: str) -> dict[str, Any]:
        if content_type not in _CONTENT_TYPE_EXTENSIONS:
            raise ValueError(f"Unsupported content type: {content_type}")
        client = self._require_client()
        key = self.build_key(report_id, content_type)
        max_bytes = self.settings.max_evidence_image_bytes
        presigned = client.generate_presigned_post(
            Bucket=self.settings.evidence_bucket_name,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, max_bytes],
            ],
            ExpiresIn=300,
        )
        return {
            "upload_url": presigned["url"],
            "fields": presigned["fields"],
            "image_key": key,
            "max_bytes": max_bytes,
        }

    def key_belongs_to_report(self, report_id: str, image_key: str) -> bool:
        return image_key.startswith(f"reports/{report_id}/") and "/.." not in image_key

    def fetch_image(self, image_key: str) -> tuple[bytes, str]:
        client = self._require_client()
        head = client.head_object(Bucket=self.settings.evidence_bucket_name, Key=image_key)
        size = int(head.get("ContentLength", 0))
        if size <= 0 or size > self.settings.max_evidence_image_bytes:
            raise EvidenceStorageError("Stored evidence image exceeds the allowed size.")
        content_type = head.get("ContentType", "")
        if content_type not in _CONTENT_TYPE_EXTENSIONS:
            raise EvidenceStorageError("Stored evidence image has an unsupported content type.")
        response = client.get_object(Bucket=self.settings.evidence_bucket_name, Key=image_key)
        body = response["Body"].read()
        return body, content_type


def _validate_assessment_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise BedrockAssessmentError("Model returned an empty assessment.")
    lowered = cleaned.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lowered:
            raise BedrockAssessmentError(
                "Model response failed advisory-language validation and was discarded."
            )
    return cleaned


class BedrockAssessmentService:
    def __init__(self, settings: Settings, runtime_client: BedrockRuntimeClient | None = None) -> None:
        self.settings = settings
        self._client = runtime_client

    def _require_client(self) -> BedrockRuntimeClient:
        if self._client is None:
            import boto3

            region = self.settings.bedrock_region or self.settings.aws_region
            self._client = boto3.client("bedrock-runtime", region_name=region)
        return self._client

    def assess_image(self, image_bytes: bytes, content_type: str) -> dict[str, Any]:
        image_format = content_type.split("/")[-1]
        client = self._require_client()
        try:
            response = client.converse(
                modelId=self.settings.bedrock_model_id,
                system=[{"text": _SYSTEM_PROMPT}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"image": {"format": image_format, "source": {"bytes": image_bytes}}},
                            {"text": "Describe what is visible in this community flood report photo."},
                        ],
                    }
                ],
                inferenceConfig={"maxTokens": 200},
            )
        except Exception as error:  # noqa: BLE001 - surfaced as a typed assessment failure
            raise BedrockAssessmentError(f"Model invocation failed: {error}") from error

        try:
            blocks = response["output"]["message"]["content"]
            text = "".join(block["text"] for block in blocks if "text" in block)
        except (KeyError, IndexError, TypeError) as error:
            raise BedrockAssessmentError("Model response was malformed.") from error

        validated_text = _validate_assessment_text(text)
        return {
            "model_id": self.settings.bedrock_model_id,
            "assessed_at": datetime.now(UTC).isoformat(),
            "summary": validated_text,
            "disclaimer": ASSESSMENT_DISCLAIMER,
        }
