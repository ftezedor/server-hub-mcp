import unittest
from unittest.mock import patch

import mcp_server


class TestGetServerMetrics(unittest.TestCase):
    @patch.object(mcp_server.client, "get_metrics")
    @patch.object(mcp_server.client, "search")
    def test_metrics_by_exact_name(self, mock_search, mock_metrics):
        mock_search.return_value = {
            "results": [{
                "id": 1, "name": "web-server-01", "ip": "192.168.1.10"
            }]
        }
        mock_metrics.return_value = {
            "server": {"id": 1, "name": "web-server-01"},
            "metrics": [{
                "cpu_usage_percent": 82.4,
                "memory_usage_percent": 71.2,
                "disk_usage_percent": 60.0,
                "timestamp": "2026-08-18T18:00:00",
            }],
            "count": 1,
        }

        result = mcp_server.get_server_metrics("web-server-01", limit=5)

        mock_metrics.assert_called_once_with(1, 5)
        self.assertEqual(result["server"]["name"], "web-server-01")
        self.assertEqual(result["count"], 1)

    @patch.object(mcp_server.client, "search")
    def test_invalid_limit(self, mock_search):
        with self.assertRaises(ValueError):
            mcp_server.get_server_metrics("web-server-01", limit=0)
        mock_search.assert_not_called()

        with self.assertRaises(ValueError):
            mcp_server.get_server_metrics("web-server-01", limit=51)

    @patch.object(mcp_server.client, "search")
    def test_unknown_server(self, mock_search):
        mock_search.return_value = {"results": []}

        with self.assertRaises(ValueError):
            mcp_server.get_server_metrics("unknown-server")


if __name__ == "__main__":
    unittest.main()
