import argparse
import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def build_payload(depth_cm: float, container_height_cm: float) -> dict[str, object]:
    return {
        "device_id": "hydrosense-simulator-01",
        "location_id": "demo-zone-01",
        "water_depth_cm": depth_cm,
        "distance_cm": max(container_height_cm - depth_cm, 0),
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": "simulated_sensor",
    }


def send_reading(api_url: str, payload: dict[str, object]) -> None:
    request = Request(
        f"{api_url.rstrip('/')}/api/v1/readings",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        print(f"HTTP {response.status}")
        print(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send an ESP32-compatible simulated water-depth reading."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--depth-cm", type=float, default=26.0)
    parser.add_argument("--container-height-cm", type=float, default=30.0)
    args = parser.parse_args()

    if args.depth_cm < 0 or args.container_height_cm <= 0:
        parser.error("depth must be non-negative and container height must be positive")
    if args.depth_cm > args.container_height_cm:
        parser.error("depth cannot exceed container height")

    payload = build_payload(args.depth_cm, args.container_height_cm)
    print(json.dumps(payload, indent=2))
    try:
        send_reading(args.api_url, payload)
    except HTTPError as error:
        raise SystemExit(f"API rejected reading: HTTP {error.code} {error.read().decode()}")
    except URLError as error:
        raise SystemExit(f"Could not reach HydroSense API: {error.reason}")


if __name__ == "__main__":
    main()
