from __future__ import annotations

import os
from typing import Any

import httpx

from app.mcp.contracts import (
    AlertsData,
    CreateAlertData,
    SearchData,
    ServerData,
    ServerDetailsData,
    ServerListData,
    ServerMetricsData,
    StatsData,
)


API_BASE_URL = os.getenv(
    "SERVER_HUB_API_URL",
    "http://localhost:8080/api",
).rstrip("/")

DEFAULT_TIMEOUT = float(
    os.getenv("SERVER_HUB_API_TIMEOUT", "10")
)


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
    ) -> None:
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
            payload = response.json()

            if not isinstance(payload, dict):
                raise RuntimeError(
                    "Server Hub API returned an invalid response payload"
                )

            return payload

        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)

            raise RuntimeError(
                f"Server Hub API error "
                f"({exc.response.status_code}): {detail}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Unable to reach Server Hub API: {exc}"
            ) from exc

    def search(self, query: str) -> SearchData:
        data = self._request(
            "GET",
            "/search",
            params={"q": query},
        )

        return SearchData.model_validate(data)

    def get_server_by_id(
        self,
        server_id: int,
    ) -> ServerDetailsData:
        data = self._request(
            "GET",
            f"/servers/{server_id}",
        )

        return ServerDetailsData.model_validate(data)

    def get_metrics(
        self,
        server_id: int,
        limit: int,
    ) -> ServerMetricsData:
        data = self._request(
            "GET",
            f"/servers/{server_id}/metrics",
            params={"limit": limit},
        )

        return ServerMetricsData.model_validate(data)

    def get_alerts(self) -> AlertsData:
        data = self._request(
            "GET",
            "/alerts",
        )

        return AlertsData.model_validate(data)

    def get_stats(self) -> StatsData:
        data = self._request(
            "GET",
            "/stats",
        )

        return StatsData.model_validate(data)

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> CreateAlertData:
        data = self._request(
            "POST",
            "/alerts",
            json={
                "server": server,
                "severity": severity,
                "message": message,
            },
        )

        return CreateAlertData.model_validate(data)

    def list_servers(self) -> ServerListData:
        data = self._request(
            "GET",
            "/servers",
        )

        return ServerListData.model_validate(data)