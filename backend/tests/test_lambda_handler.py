import json
from dataclasses import dataclass

from app.lambda_handler import handler


@dataclass
class LambdaContext:
    function_name: str = "hydrosense-test"
    function_version: str = "$LATEST"
    invoked_function_arn: str = "arn:aws:lambda:ap-south-1:123456789012:function:test"
    memory_limit_in_mb: int = 512
    aws_request_id: str = "test-request"
    log_group_name: str = "/aws/lambda/hydrosense-test"
    log_stream_name: str = "test-stream"
    identity: None = None
    client_context: None = None

    def get_remaining_time_in_millis(self) -> int:
        return 10_000


def test_http_api_health_event() -> None:
    event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "example.execute-api.ap-south-1.amazonaws.com"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api",
            "domainName": "example.execute-api.ap-south-1.amazonaws.com",
            "domainPrefix": "example",
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "test-request",
            "routeKey": "GET /health",
            "stage": "$default",
            "time": "10/Oct/2026:00:00:00 +0000",
            "timeEpoch": 1_791_590_400_000,
        },
        "isBase64Encoded": False,
    }

    response = handler(event, LambdaContext())

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "status": "ok",
        "service": "hydrosense-api",
        "version": "0.2.0",
    }