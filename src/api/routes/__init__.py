# src/api/routes/__init__.py
"""
API Router Module
Exportiert alle verfügbaren Router
"""

from src.api.routes import vehicles
from src.api.routes import process
from src.api.routes import dashboard
from src.api.routes import info

__all__ = [
    "vehicles",
    "process",
    "dashboard",
    "info"
]