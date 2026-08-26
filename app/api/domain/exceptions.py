class DomainError(Exception):
    """Base exception for application/domain errors."""


class ServerNotFoundError(DomainError):
    def __init__(self, identifier: str | int):
        super().__init__(f"Server '{identifier}' not found")


class DuplicateServerError(DomainError):
    def __init__(self, name: str):
        super().__init__(f"Server '{name}' already exists")


class ValidationError(DomainError):
    pass
