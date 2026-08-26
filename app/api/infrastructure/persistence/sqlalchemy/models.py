from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class ServerModel(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offline")
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_gb: Mapped[float] = mapped_column(Float, nullable=False)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=True)


class MetricsModel(Base):
    __tablename__ = "server_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=False)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=True)


class AlertModel(Base):
    __tablename__ = "server_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
