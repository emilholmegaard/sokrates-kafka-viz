import pytest
from pathlib import Path

@pytest.fixture
def test_data_dir() -> Path:
    """Returns path to test data directory."""
    return Path(__file__).parent / 'test_data'

@pytest.fixture
def java_service_dir(test_data_dir) -> Path:
    """Returns path to Java test service directory."""
    return test_data_dir / 'java_service'

@pytest.fixture
def python_service_dir(test_data_dir) -> Path:
    """Returns path to Python test service directory."""
    return test_data_dir / 'python_service'

@pytest.fixture
def spring_service_dir(test_data_dir) -> Path:
    """Returns path to Spring Cloud Stream test service directory."""
    return test_data_dir / 'spring_service'