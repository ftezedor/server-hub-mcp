import unittest
from unittest.mock import patch

import mcp_server


class TestGetSystemStats(unittest.TestCase):
    @patch.object(mcp_server.client, "get_stats")
    def test_returns_system_stats(self, mock_stats):
        expected = {
            "total_servers": 10,
            "servers_by_status": {
                "online": 8,
                "offline": 1,
                "maintenance": 1,
            },
            "active_alerts": 3,
            "alerts_by_severity": {
                "critical": 1,
                "warning": 1,
                "info": 1,
            },
        }
        mock_stats.return_value = expected

        result = mcp_server.get_system_stats()

        self.assertEqual(result, expected)
        mock_stats.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
