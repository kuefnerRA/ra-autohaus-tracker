# tests/conftest.py
import pytest
import os
from unittest.mock import Mock

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Test-Umgebung konfigurieren"""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PROJECT_ID"] = "test-project"
    os.environ["BIGQUERY_DATASET"] = "test_dataset"

@pytest.fixture
def mock_bigquery_service():
    """Mock BigQuery Service für alle Tests"""
    mock = Mock()
    mock.health_check.return_value = True
    mock.create_vehicle.return_value = True
    mock.create_process.return_value = True
    return mock