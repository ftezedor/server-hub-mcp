from datetime import datetime

from unittest.mock import patch

from app.mcp.contracts import AlertData, AlertsData

import app.mcp.server as server


def test_active_alerts_use_server_reference_from_backend():
    alerts = AlertsData(
        alerts=[
            AlertData(
                id=42,
                server="web-server-01",
                server_ip="192.168.1.10",
                severity="critical",
                message="High CPU usage",
                resolved=False,
                created_at=datetime.fromisoformat(
                    "2026-08-18T18:00:00"
                ).isoformat(),
            )
        ],
        total=1,
    )

    with (
        patch.object(
            server.client,
            "get_alerts",
            return_value=alerts,
        ) as mock_alerts,
        patch.object(
            server.client,
            "search",
            side_effect=AssertionError("unexpected search"),
        ),
        patch.object(
            server.client,
            "get_server_by_id",
            side_effect=AssertionError("unexpected server lookup"),
        ),
    ):
        result = server.get_active_alerts()

    assert result.count == 1

    alert = result.alerts[0]

    assert alert.server is not None
    assert alert.server.name == "web-server-01"
    assert alert.server.ip == "192.168.1.10"
    assert alert.severity == "critical"
    assert alert.message == "High CPU usage"
    assert result.warnings == []

    mock_alerts.assert_called_once_with()


def test_active_alerts_warn_when_server_reference_is_incomplete():
    alerts = AlertsData(
        alerts=[
            AlertData(
                id=42,
                server="web-server-01",
                server_ip=None,
                severity="critical",
                message="High CPU usage",
                resolved=False,
                created_at=datetime.fromisoformat(
                    "2026-08-18T18:00:00"
                ).isoformat(),
            )
        ],
        total=1,
    )

    with patch.object(
        server.client,
        "get_alerts",
        return_value=alerts,
    ):
        result = server.get_active_alerts()

    assert result.count == 1
    assert result.alerts[0].server is None
    assert len(result.warnings) == 1
    assert result.warnings[0].type == "server_reference_incomplete"


def test_no_active_alerts():
    alerts = AlertsData(
        alerts=[],
        total=0,
    )

    with patch.object(
        server.client,
        "get_alerts",
        return_value=alerts,
    ):
        result = server.get_active_alerts()

    assert result.alerts == []
    assert result.count == 0
    assert result.warnings == []