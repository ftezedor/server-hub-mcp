from __future__ import annotations

import os
from typing import Any

import httpx


API_BASE_URL = os.getenv(
    "SERVER_HUB_API_URL",
    "http://localhost:8080/api",
).rstrip("/")
DEFAULT_TIMEOUT = float(os.getenv("SERVER_HUB_API_TIMEOUT", "10"))


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            return str(payload["detail"])
    except ValueError:
        pass
    return response.text or response.reason_phrase


class RestServerHubClient:
    """Server Hub client backed by the REST API."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        print(f"Server Hub API: {self.base_url}")

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            raise RuntimeError(
                f"Server Hub API error ({exc.response.status_code}): {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Unable to reach Server Hub API: {exc}"
            ) from exc

    def search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/search", params={"q": query})

    def get_server_by_id(self, server_id: int) -> dict[str, Any]:
        return self._request("GET", f"/servers/{server_id}")

    def get_metrics(self, server_id: int, limit: int) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/servers/{server_id}/metrics",
            params={"limit": limit},
        )

    def get_alerts(self) -> dict[str, Any]:
        return self._request("GET", "/alerts")

    def get_stats(self) -> dict[str, Any]:
        return self._request("GET", "/stats")

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/alerts",
            json={
                "server": server,
                "severity": severity,
                "message": message,
            },
        )
