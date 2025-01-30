import pytest
from pathlib import Path

@pytest.fixture
def test_project_path(test_data_dir):
    """Directory containing test project data."""
    return Path(test_data_dir) / "java"