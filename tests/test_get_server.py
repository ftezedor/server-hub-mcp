import unittest
from unittest.mock import patch

import mcp_server


class TestGetServer(unittest.TestCase):
    @patch.object(mcp_server.client, "get_server_by_id")
    @patch.object(mcp_server.client, "search")
    def test_exact_name(self, mock_search, mock_get):
        mock_search.return_value = {
            "results": [{
                "id": 1, "name": "web-server-01", "ip": "192.168.1.10",
                "environment": "production", "status": "online",
            }]
        }
        mock_get.return_value = {
            "id": 1, "name": "web-server-01", "ip": "192.168.1.10",
            "environment": "production", "status": "online",
            "cpu_cores": 8, "memory_gb": 16, "disk_gb": 500,
        }

        result = mcp_server.get_server("web-server-01")

        self.assertEqual(result["name"], "web-server-01")
        self.assertNotIn("id", result)
        mock_get.assert_called_once_with(1)

    @patch.object(mcp_server.client, "get_server_by_id")
    @patch.object(mcp_server.client, "search")
    def test_exact_ip(self, mock_search, mock_get):
        mock_search.return_value = {
            "results": [{
                "id": 1, "name": "web-server-01", "ip": "192.168.1.10"
            }]
        }
        mock_get.return_value = {
            "id": 1, "name": "web-server-01", "ip": "192.168.1.10"
        }

        result = mcp_server.get_server("192.168.1.10")

        self.assertEqual(result["ip"], "192.168.1.10")

    @patch.object(mcp_server.client, "search")
    def test_partial_name_is_not_accepted(self, mock_search):
        mock_search.return_value = {
            "results": [{
                "id": 1, "name": "web-server-01", "ip": "192.168.1.10"
            }]
        }

        with self.assertRaises(ValueError):
            mcp_server.get_server("web")

    @patch.object(mcp_server.client, "search")
    def test_not_found(self, mock_search):
        mock_search.return_value = {"results": []}

        with self.assertRaises(ValueError):
            mcp_server.get_server("unknown-server")


if __name__ == "__main__":
    unittest.main()
