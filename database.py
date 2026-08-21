import sqlite3
from datetime import datetime
from typing import List, Optional
from models import Server, ServerMetrics, ServerAlert

DATABASE_PATH = "servers.db"

def get_db_connection():
    """Retorna conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa o banco de dados com as tabelas necessárias."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de servidores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            ip TEXT NOT NULL,
            environment TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'offline',
            cpu_cores INTEGER NOT NULL,
            memory_gb REAL NOT NULL,
            disk_gb REAL NOT NULL,
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de métricas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            cpu_usage_percent REAL NOT NULL,
            memory_usage_percent REAL NOT NULL,
            disk_usage_percent REAL NOT NULL,
            temperature_celsius REAL,
            uptime_seconds INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
    """)
    
    # Tabela de alertas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            resolved BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")

# ============ CRUD para Servers ============

def create_server(server: Server) -> int:
    """Adiciona um novo servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO servers (name, ip, environment, status, cpu_cores, memory_gb, disk_gb)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (server.name, server.ip, server.environment, server.status, 
          server.cpu_cores, server.memory_gb, server.disk_gb))
    
    server_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return server_id

def get_all_servers() -> List[dict]:
    """Retorna todos os servidores."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servers ORDER BY name")
    servers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return servers

def get_server_by_id(server_id: int) -> Optional[dict]:
    """Retorna um servidor pelo ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
    server = cursor.fetchone()
    conn.close()
    return dict(server) if server else None

def get_server_by_name(name: str) -> Optional[dict]:
    """Retorna um servidor pelo nome."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servers WHERE name = ?", (name,))
    server = cursor.fetchone()
    conn.close()
    return dict(server) if server else None

def update_server_status(server_id: int, status: str):
    """Atualiza o status de um servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE servers 
        SET status = ?, last_updated = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, server_id))
    conn.commit()
    conn.close()

def delete_server(server_id: int):
    """Remove um servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    conn.commit()
    conn.close()

# ============ Métricas ============

def add_metrics(metrics: ServerMetrics) -> int:
    """Adiciona métricas para um servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO server_metrics 
        (server_id, cpu_usage_percent, memory_usage_percent, disk_usage_percent, 
         temperature_celsius, uptime_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (metrics.server_id, metrics.cpu_usage_percent, metrics.memory_usage_percent,
          metrics.disk_usage_percent, metrics.temperature_celsius, metrics.uptime_seconds))
    
    metrics_id = cursor.lastrowid
    if metrics_id is None:
        conn.close()
        raise RuntimeError("Failed to retrieve the inserted metrics ID")
    conn.commit()
    conn.close()
    return metrics_id

def get_latest_metrics(server_id: int) -> Optional[dict]:
    """Retorna as métricas mais recentes de um servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM server_metrics 
        WHERE server_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (server_id,))
    metrics = cursor.fetchone()
    conn.close()
    return dict(metrics) if metrics else None

def get_metrics_history(server_id: int, limit: int = 10) -> List[dict]:
    """Retorna histórico de métricas de um servidor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM server_metrics 
        WHERE server_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (server_id, limit))
    metrics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return metrics

# ============ Alertas ============

def create_alert(alert: ServerAlert) -> int:
    """Cria um novo alerta."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO server_alerts (server_id, severity, message)
        VALUES (?, ?, ?)
    """, (alert.server_id, alert.severity, alert.message))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_active_alerts() -> List[dict]:
    """Retorna alertas não resolvidos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM server_alerts 
        WHERE resolved = 0 
        ORDER BY created_at DESC
    """)
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alerts

def resolve_alert(alert_id: int):
    """Marca um alerta como resolvido."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE server_alerts 
        SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (alert_id,))
    conn.commit()
    conn.close()