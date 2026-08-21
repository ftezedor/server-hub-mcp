import unittest
from unittest.mock import patch

import mcp_server


class TestGetActiveAlerts(unittest.TestCase):
    @patch.object(mcp_server.client, "get_server_by_id")
    @patch.object(mcp_server.client, "get_alerts")
    def test_active_alerts_hide_ids(self, mock_alerts, mock_server):
        mock_alerts.return_value = {
            "alerts": [{
                "id": 42,
                "server_id": 1,
                "severity": "critical",
                "message": "High CPU usage",
                "created_at": "2026-08-18T18:00:00",
            }]
        }
        mock_server.return_value = {
            "id": 1,
            "name": "web-server-01",
            "ip": "192.168.1.10",
        }

        result = mcp_server.get_active_alerts()

        self.assertEqual(result["count"], 1)
        alert = result["alerts"][0]
        self.assertEqual(alert["server"]["name"], "web-server-01")
        self.assertEqual(alert["severity"], "critical")
        self.assertNotIn("id", alert)
        self.assertNotIn("server_id", alert)
        mock_server.assert_called_once_with(1)

    @patch.object(mcp_server.client, "get_alerts")
    def test_no_active_alerts(self, mock_alerts):
        mock_alerts.return_value = {"alerts": []}

        result = mcp_server.get_active_alerts()

        self.assertEqual(result, {"alerts": [], "count": 0})


if __name__ == "__main__":
    unittest.main()
