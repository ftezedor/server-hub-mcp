import unittest
from unittest.mock import patch

import mcp_server


class TestCreateAlert(unittest.TestCase):
    @patch.object(mcp_server.client, "create_alert")
    @patch.object(mcp_server.client, "search")
    def test_create_alert_by_exact_name(self, mock_search, mock_create):
        mock_search.return_value = {
            "results": [{
                "id": 1, "name": "web-server-01", "ip": "192.168.1.10"
            }]
        }
        mock_create.return_value = {
            "id": 99,
            "message": "Alerta criado com sucesso",
        }

        result = mcp_server.create_alert(
            "web-server-01",
            "CRITICAL",
            "CPU usage exceeded threshold",
        )

        mock_create.assert_called_once_with(
            1, "critical", "CPU usage exceeded threshold"
        )
        self.assertTrue(result["created"])
        self.assertEqual(result["server"]["name"], "web-server-01")
        self.assertNotIn("id", result)

    @patch.object(mcp_server.client, "search")
    def test_invalid_severity(self, mock_search):
        with self.assertRaises(ValueError):
            mcp_server.create_alert("web-server-01", "fatal", "Something happened")
        mock_search.assert_not_called()

    @patch.object(mcp_server.client, "search")
    def test_empty_message(self, mock_search):
        with self.assertRaises(ValueError):
            mcp_server.create_alert("web-server-01", "warning", "   ")
        mock_search.assert_not_called()

    @patch.object(mcp_server.client, "search")
    def test_unknown_server(self, mock_search):
        mock_search.return_value = {"results": []}

        with self.assertRaises(ValueError):
            mcp_server.create_alert("unknown-server", "warning", "Test")


if __name__ == "__main__":
    unittest.main()
