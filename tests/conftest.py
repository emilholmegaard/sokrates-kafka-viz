from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir() -> Path:
    """Fixture providing path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def python_service_dir(test_data_dir) -> Path:
    """Fixture providing path to Python test service."""
    return test_data_dir / "python_service"


@pytest.fixture
def spring_service_dir(test_data_dir) -> Path:
    """Fixture providing path to Spring test service."""
    return test_data_dir / "spring_service"


def test_project_path(test_data_dir):
    """Directory containing test project data."""
    return Path(test_data_dir) / "java"
