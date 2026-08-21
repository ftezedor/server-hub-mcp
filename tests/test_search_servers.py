import unittest
from unittest.mock import patch

import mcp_server


class TestSearchServers(unittest.TestCase):
    @patch.object(mcp_server.client, "search")
    def test_partial_name_search(self, mock_search):
        mock_search.return_value = {
            "query": "web",
            "results": [
                {
                    "id": 1, "name": "web-server-01", "ip": "192.168.1.10",
                    "environment": "production", "status": "online",
                },
                {
                    "id": 2, "name": "web-server-02", "ip": "192.168.1.11",
                    "environment": "staging", "status": "offline",
                },
            ],
            "count": 2,
        }

        result = mcp_server.search_servers("web")

        mock_search.assert_called_once_with("web")
        self.assertEqual(result["query"], "web")
        self.assertEqual(len(result["servers"]), 2)
        self.assertNotIn("id", result["servers"][0])

    def test_empty_query_rejected(self):
        with self.assertRaises(ValueError):
            mcp_server.search_servers("   ")


if __name__ == "__main__":
    unittest.main()
