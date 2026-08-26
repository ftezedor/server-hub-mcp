from app.api.application.ports import MetricsRepository
from app.api.domain.entities import ServerMetrics


class MetricsService:
    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def add(self, metrics: ServerMetrics) -> ServerMetrics:
        return self.repository.save(metrics)

    def latest(self, server_id: int) -> ServerMetrics | None:
        return self.repository.find_latest(server_id)

    def history(self, server_id: int, limit: int = 10) -> list[ServerMetrics]:
        return self.repository.find_history(server_id, limit)
