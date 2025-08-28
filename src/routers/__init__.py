from .integration import router as integration_router

# Placeholder für weitere Router (werden später erstellt)
try:
    from .vehicles import router as vehicles_router
except ImportError:
    vehicles_router = None

try:
    from .processes import router as processes_router  
except ImportError:
    processes_router = None

try:
    from .dashboard import router as dashboard_router
except ImportError:
    dashboard_router = None

__all__ = [
    "integration_router",
    "vehicles_router", 
    "processes_router",
    "dashboard_router"
]