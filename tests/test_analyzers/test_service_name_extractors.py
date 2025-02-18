import pytest
from pathlib import Path
import xml.etree.ElementTree as ET

def test_java_service_name_extractor_pom_xml(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import JavaServiceNameExtractor
    
    extractor = JavaServiceNameExtractor()
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <artifactId>test-service</artifactId>
        <name>Test Service Name</name>
    </project>"""
    
    def mock_parse(file_path):
        tree = ET.ElementTree(ET.fromstring(pom_content))
        return tree

    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(Path("/some/path/pom.xml"))
    assert result == "test-service"

def test_java_service_name_extractor_fallback(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import JavaServiceNameExtractor
    
    extractor = JavaServiceNameExtractor()
    
    def mock_parse(file_path):
        raise ET.ParseError()
    
    monkeypatch.setattr(ET, "parse", mock_parse)
    monkeypatch.setattr(Path, "parent", lambda self: Path("/mock/fallback-name"))
    
    result = extractor.extract(Path("/mock/path/pom.xml"))
    assert result == "fallback-name"

def test_javascript_service_name_extractor(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import JavaScriptServiceNameExtractor
    
    extractor = JavaScriptServiceNameExtractor()
    package_content = '{"name": "@scope/test-service"}'
    
    def mock_open(file, mode='r', *args, **kwargs):
        from io import StringIO
        return StringIO(package_content)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    result = extractor.extract(Path("package.json"))
    assert result == "test-service"

def test_python_service_name_extractor_pyproject(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import PythonServiceNameExtractor
    
    extractor = PythonServiceNameExtractor()
    pyproject_content = """
    [project]
    name = "test-service"
    """
    
    monkeypatch.setattr(Path, "read_text", lambda self: pyproject_content)
    
    result = extractor.extract(Path("pyproject.toml"))
    assert result == "test-service"

def test_csharp_service_name_extractor(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import CSharpServiceNameExtractor
    
    extractor = CSharpServiceNameExtractor()
    csproj_content = """<?xml version="1.0" encoding="utf-8"?>
    <Project>
        <PropertyGroup>
            <AssemblyName>test-service</AssemblyName>
        </PropertyGroup>
    </Project>"""
    
    def mock_parse(file_path):
        tree = ET.ElementTree(ET.fromstring(csproj_content))
        return tree
    
    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(Path("test.csproj"))
    assert result == "test-service"

def test_name_sanitization():
    from kafka_viz.analyzers.service_name_extractors import ServiceNameExtractor
    
    class TestExtractor(ServiceNameExtractor):
        def extract(self, build_file):
            pass
    
    extractor = TestExtractor()
    
    assert extractor._sanitize_name("testService") == "test-service"
    assert extractor._sanitize_name("test service") == "test-service"
    assert extractor._sanitize_name("test_service") == "test-service"
    assert extractor._sanitize_name("test@service!") == "testservice"
    assert extractor._sanitize_name("") == ""
    assert extractor._sanitize_name("TestService_NAME") == "test-service-name"

def test_error_handling(monkeypatch):
    from kafka_viz.analyzers.service_name_extractors import (
        JavaServiceNameExtractor,
        JavaScriptServiceNameExtractor,
        PythonServiceNameExtractor,
        CSharpServiceNameExtractor,
    )
    
    # Test Java extractor with invalid XML
    java_extractor = JavaServiceNameExtractor()
    def mock_parse_error(file_path):
        raise ET.ParseError()
    
    monkeypatch.setattr(ET, "parse", mock_parse_error)
    monkeypatch.setattr(Path, "parent", lambda self: Path("/mock/fallback-name"))
    
    result = java_extractor.extract(Path("/mock/path/pom.xml"))
    assert result == "fallback-name"
    
    # Test JavaScript extractor with invalid JSON
    js_extractor = JavaScriptServiceNameExtractor()
    def mock_open_error(file, mode='r', *args, **kwargs):
        from io import StringIO
        return StringIO("invalid json")
    
    monkeypatch.setattr("builtins.open", mock_open_error)
    monkeypatch.setattr(Path, "parent", lambda self: Path("/mock/fallback-name"))
    
    result = js_extractor.extract(Path("/mock/path/package.json"))
    assert result == "fallback-name"