import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import pytest

from kafka_viz.analyzers.service_name_extractors import (
    CSharpServiceNameExtractor,
    JavaScriptServiceNameExtractor,
    JavaServiceNameExtractor,
    PythonServiceNameExtractor,
)


class MockPath:
    """Mock Path object with configurable properties"""

    def __init__(self, name: str, parent_name: str = "parent"):
        self._name = name
        self._parent_name = parent_name
        self._content = ""

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> "MockPath":
        return MockPath(self._parent_name)

    @property
    def stem(self) -> str:
        """Return file name without extension"""
        return self._name.rsplit(".", 1)[0]

    def __str__(self) -> str:
        return f"/mock/path/{self._name}"

    def __fspath__(self) -> str:
        """Make the mock path compatible with os.PathLike"""
        return str(self)

    def exists(self) -> bool:
        return True

    def read_text(self) -> str:
        return self._content

    def set_content(self, content: str) -> None:
        self._content = content


class MockXmlElement:
    def __init__(self, text: Optional[str] = None):
        self.text = text


class MockXmlTree:
    def __init__(self, elements: dict[str, str]):
        self._elements = {k: MockXmlElement(v) for k, v in elements.items()}

    def find(self, path: str) -> Optional[MockXmlElement]:
        # Strip .//, //, and ./ from path
        clean_path = path.replace(".//", "").replace("//", "").replace("./", "")
        return self._elements.get(clean_path)

    def getroot(self) -> "MockXmlTree":
        return self


@pytest.fixture
def mock_path():
    return MockPath("test-file")


@pytest.fixture
def java_extractor():
    return JavaServiceNameExtractor()


@pytest.fixture
def js_extractor():
    return JavaScriptServiceNameExtractor()


@pytest.fixture
def python_extractor():
    return PythonServiceNameExtractor()


@pytest.fixture
def csharp_extractor():
    return CSharpServiceNameExtractor()


def test_java_service_name_extractor_pom(java_extractor, monkeypatch):
    mock_file = MockPath("pom.xml")

    def mock_parse(*args, **kwargs):
        elements = {"artifactId": "test-service"}
        return MockXmlTree(elements)

    monkeypatch.setattr(ET, "parse", mock_parse)

    result = java_extractor.extract(mock_file)
    assert result == "test-service"


def test_java_service_name_extractor_gradle(java_extractor):
    mock_file = MockPath("build.gradle")
    mock_file.set_content("rootProject.name = 'test-service'")

    result = java_extractor.extract(mock_file)
    assert result == "test-service"


def test_java_service_name_extractor_fallback(java_extractor, monkeypatch):
    mock_file = MockPath("pom.xml", parent_name="fallback-service")

    def mock_parse(*args, **kwargs):
        raise ET.ParseError()

    def mock_exists(*args, **kwargs):
        return False

    monkeypatch.setattr(ET, "parse", mock_parse)
    monkeypatch.setattr(Path, "exists", mock_exists)

    result = java_extractor.extract(mock_file)
    assert result == "fallback-service"


def test_js_service_name_extractor_package(js_extractor, monkeypatch):
    mock_file = MockPath("package.json")
    package_content = '{"name": "@scope/test-service"}'
    mock_file.set_content(package_content)

    result = js_extractor.extract(mock_file)
    assert result == "test-service"


def test_js_service_name_extractor_fallback(js_extractor):
    mock_file = MockPath("package.json", parent_name="fallback-service")
    mock_file.set_content("{}")

    result = js_extractor.extract(mock_file)
    assert result == "fallback-service"


def test_python_service_name_extractor_setup(python_extractor):
    setup_content = """
    from setuptools import setup
    setup(name='test-service')
    """
    mock_file = MockPath("setup.py")
    mock_file.set_content(setup_content)

    result = python_extractor.extract(mock_file)
    assert result == "test-service"


def test_python_service_name_extractor_pyproject(python_extractor):
    mock_file = MockPath("pyproject.toml")
    mock_file.set_content('[project]\nname = "test-service"')

    result = python_extractor.extract(mock_file)
    assert result == "test-service"


def test_python_service_name_extractor_requirements(python_extractor):
    mock_file = MockPath("requirements.txt", parent_name="test-service")

    result = python_extractor.extract(mock_file)
    assert result == "test-service"


def test_csharp_service_name_extractor_assembly(csharp_extractor, monkeypatch):
    mock_file = MockPath("test.csproj")

    def mock_parse(*args: Any, **kwargs: Any) -> Any:
        elements = {"AssemblyName": "TestService"}
        return MockXmlTree(elements)

    monkeypatch.setattr(ET, "parse", mock_parse)

    result = csharp_extractor.extract(mock_file)
    assert result == "test-service"


def test_csharp_service_name_extractor_fallback(csharp_extractor, monkeypatch):
    mock_file = MockPath("test-service.csproj")

    def mock_parse(*args: Any, **kwargs: Any) -> None:
        raise ET.ParseError()

    monkeypatch.setattr(ET, "parse", mock_parse)

    result = csharp_extractor.extract(mock_file)
    assert result == "test-service"
