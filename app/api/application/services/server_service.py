from app.api.application.ports import ServerRepository
from app.api.domain.entities import Server
from app.api.domain.enums import ServerStatus
from app.api.domain.exceptions import DuplicateServerError, ServerNotFoundError


class ServerService:
    def __init__(self, repository: ServerRepository):
        self.repository = repository

    def list_servers(self) -> list[Server]:
        return self.repository.find_all()

    def search_servers(self, query: str) -> list[Server]:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        return self.repository.search(query.strip())

    def get_server(self, server_id: int) -> Server:
        server = self.repository.find_by_id(server_id)
        if not server:
            raise ServerNotFoundError(server_id)
        return server

    def find_by_identifier(self, identifier: str) -> Server:
        server = self.repository.find_by_name(identifier) or self.repository.find_by_ip(identifier)
        if not server:
            raise ServerNotFoundError(identifier)
        return server

    def create_server(self, server: Server) -> Server:
        if self.repository.find_by_name(server.name):
            raise DuplicateServerError(server.name)
        return self.repository.save(server)

    def update_status(self, server_id: int, status: ServerStatus) -> Server:
        self.get_server(server_id)
        self.repository.update_status(server_id, status)
        return self.get_server(server_id)

    def delete_server(self, server_id: int) -> None:
        self.get_server(server_id)
        self.repository.delete(server_id)

    def find_by_id(self, server_id: int) -> Server | None:
        return self.repository.find_by_id(server_id)