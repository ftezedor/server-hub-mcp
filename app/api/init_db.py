# init_db.py (versão melhorada)
from database import init_database, create_server, add_metrics, create_alert, get_server_by_name
from app.mcp.models import Server, ServerMetrics, ServerAlert
import random

def seed_database():
    """Popula o banco com dados de exemplo."""
    print("🌱 Inicializando banco de dados com dados de exemplo...")
    
    # Servidores de exemplo
    servers_data = [
        {"name": "web-server-01", "ip": "192.168.1.10", "environment": "production", 
         "status": "online", "cpu_cores": 8, "memory_gb": 16, "disk_gb": 500},
        {"name": "web-server-02", "ip": "192.168.1.11", "environment": "production", 
         "status": "online", "cpu_cores": 8, "memory_gb": 16, "disk_gb": 500},
        {"name": "db-server-01", "ip": "192.168.1.20", "environment": "production", 
         "status": "online", "cpu_cores": 16, "memory_gb": 64, "disk_gb": 2000},
        {"name": "cache-server-01", "ip": "192.168.1.30", "environment": "staging", 
         "status": "online", "cpu_cores": 4, "memory_gb": 8, "disk_gb": 100},
        {"name": "api-server-01", "ip": "192.168.1.40", "environment": "development", 
         "status": "maintenance", "cpu_cores": 4, "memory_gb": 8, "disk_gb": 200},
    ]
    
    server_ids = {}
    for data in servers_data:
        # Verifica se o servidor já existe
        existing = get_server_by_name(data['name'])
        if existing:
            print(f"  ⏭️ Servidor '{data['name']}' já existe (ID: {existing['id']})")
            server_ids[data['name']] = existing['id']
            continue
        
        server = Server(**data)
        server_id = create_server(server)
        server_ids[data['name']] = server_id
        print(f"  ✅ Servidor '{data['name']}' criado (ID: {server_id})")
    
    # Métricas de exemplo
    for name, server_id in server_ids.items():
        # Verifica se já tem métricas para este servidor
        from database import get_latest_metrics
        if get_latest_metrics(server_id):
            print(f"  ⏭️ Métricas já existem para '{name}'")
            continue
            
        for _ in range(5):
            metrics = ServerMetrics(
                server_id=server_id,
                cpu_usage_percent=round(random.uniform(10, 90), 1),
                memory_usage_percent=round(random.uniform(20, 85), 1),
                disk_usage_percent=round(random.uniform(30, 80), 1),
                temperature_celsius=round(random.uniform(35, 75), 1),
                uptime_seconds=random.randint(3600, 86400 * 30)
            )
            add_metrics(metrics)
        print(f"  📊 Métricas adicionadas para '{name}'")
    
    # Alertas de exemplo
    alerts_data = [
        {"server_id": server_ids.get("db-server-01"), "severity": "warning", 
         "message": "Uso de CPU acima de 80% por 5 minutos"},
        {"server_id": server_ids.get("web-server-02"), "severity": "critical", 
         "message": "Servidor inacessível - timeout de conexão"},
        {"server_id": server_ids.get("api-server-01"), "severity": "info", 
         "message": "Manutenção programada para atualização de versão"},
    ]
    
    for alert_data in alerts_data:
        if not alert_data["server_id"]:
            continue
            
        # Verifica se o alerta já existe (evita duplicatas)
        from database import get_active_alerts
        existing_alerts = get_active_alerts()
        if any(a['server_id'] == alert_data['server_id'] and a['message'] == alert_data['message'] 
               for a in existing_alerts):
            print(f"  ⏭️ Alerta já existe: {alert_data['message']}")
            continue
            
        alert = ServerAlert(**alert_data)
        create_alert(alert)
        print(f"  ⚠️ Alerta criado: {alert_data['message']}")
    
    print("✅ Banco de dados populado com sucesso!")

if __name__ == "__main__":
    init_database()
    seed_database()