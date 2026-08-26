from fastapi import APIRouter, Depends, status
from app.api.schemas import AlertCreate, AlertResponse
from app.api.container import services

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=dict)
def list_alerts(dep=Depends(services)):
    alerts = [
        AlertResponse.model_validate(a)
        for a in dep["alerts"].active()
    ]
    return {"alerts": alerts, "total": len(alerts)}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_alert_endpoint(payload: AlertCreate, dep=Depends(services)):
    alert = dep["alerts"].create(
        server=payload.server,
        severity=payload.severity,
        message=payload.message,
    )

    return {
        "id": alert.id,
        "message": "Alerta criado com sucesso",
        "created_at": (
            alert.created_at.isoformat()
            if alert.created_at is not None
            else None
        ),
    }