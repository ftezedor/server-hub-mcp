# MCP tool tests

Each MCP tool has its own standalone test script:

```text
tests/
├── test_search_servers.py
├── test_get_server.py
├── test_get_server_metrics.py
├── test_get_active_alerts.py
├── test_get_system_stats.py
└── test_create_alert.py
```

The tests exercise the MCP layer without requiring the REST API or database.
The REST client is mocked so these tests focus on MCP contracts, validation,
identifier resolution, and ID hiding.

Run all tests:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Run one tool:

```bash
python -m unittest tests.test_get_server -v
```

These are unit/contract tests. A separate integration test should later run
against the real Server Hub REST API.
