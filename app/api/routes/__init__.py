from .alerts import router as alerts_router
from .metrics import router as metrics_router
from .search import router as search_router
from .servers import router as servers_router
from .stats import router as stats_router

__all__ = ["servers_router", "metrics_router", "alerts_router", "search_router", "stats_router"]
