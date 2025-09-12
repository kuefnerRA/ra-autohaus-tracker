"""Minimaler Test für EmailService"""
import pytest
from unittest.mock import Mock
from src.services.email_service import EmailService

def test_email_service_creation():
    """Test dass EmailService erstellt werden kann"""
    mock_vehicle = Mock()
    mock_bigquery = Mock()
    
    service = EmailService(
        mock_vehicle,
        mock_bigquery,
        'test@test.com',
        'password',
        'imap.test.com'
    )
    
    assert service is not None