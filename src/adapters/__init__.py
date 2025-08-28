# src/adapters/__init__.py
from .zapier_adapter import ZapierAdapter
from .email_adapter import EmailAdapter
from .webhook_adapter import WebhookAdapter

__all__ = [
    "ZapierAdapter",
    "EmailAdapter", 
    "WebhookAdapter"
]