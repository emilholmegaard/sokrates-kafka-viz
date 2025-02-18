import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
from kafka_viz.analyzers.service_name_extractors import (
    JavaServiceNameExtractor,
    JavaScriptServiceNameExtractor,
    PythonServiceNameExtractor,
    CSharpServiceNameExtractor,
)

def test_java_service_name_extractor_pom_xml(monkeypatch):
    extractor = JavaServiceNameExtractor()
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <artifactId>test-service</artifactId>
        <name>Test Service Name</name>
    </project>"""
    
    # Create the XML structure directly
    root = ET.Element("project")
    root.set("xmlns", "http://maven.apache.org/POM/4.0.0")
    artifactId = ET.SubElement(root, "artifactId")
    artifactId.text = "test-service"
    
    def mock_parse(file_path):
        class MockTree:
            def getroot(self):
                return root
        return MockTree()
    
    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(Path("/some/path/pom.xml"))
    assert result == "test-service"

def test_java_service_name_extractor_fallback(monkeypatch):
    extractor = JavaServiceNameExtractor()
    
    def mock_parse(file_path):
        raise ET.ParseError()
    
    class MockPath:
        @property
        def name(self):
            return "fallback-name"
    
    monkeypatch.setattr(Path, "parent", lambda _: MockPath())
    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(Path("/mock/path/pom.xml"))
    assert result == "fallback-name"

def test_javascript_service_name_extractor(monkeypatch):
    extractor = JavaScriptServiceNameExtractor()
    package_content = '{"name": "@scope/test-service"}'
    
    def mock_open(file, mode='r', *args, **kwargs):
        from io import StringIO
        return StringIO(package_content)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    result = extractor.extract(Path("package.json"))
    assert result == "test-service"

def test_python_service_name_extractor_setup_py(monkeypatch):
    extractor = PythonServiceNameExtractor()
    setup_py_content = """
    from setuptools import setup

    setup(
        name='test-service',
        version='1.0.0'
    )
    """
    
    monkeypatch.setattr(Path, "read_text", lambda self: setup_py_content)
    
    result = extractor.extract(Path("setup.py"))
    assert result == "test-service"

def test_python_service_name_extractor_pyproject_toml(monkeypatch):
    extractor = PythonServiceNameExtractor()
    pyproject_content = """
    [project]
    name = "test-service"
    version = "1.0.0"
    """
    
    monkeypatch.setattr(Path, "read_text", lambda self: pyproject_content)
    
    result = extractor.extract(Path("pyproject.toml"))
    assert result == "test-service"

def test_python_service_name_extractor_requirements_txt(monkeypatch):
    extractor = PythonServiceNameExtractor()
    
    class MockPath:
        @property
        def name(self):
            return "test-service"
    
    monkeypatch.setattr(Path, "parent", lambda _: MockPath())
    
    result = extractor.extract(Path("requirements.txt"))
    assert result == "test-service"

def test_csharp_service_name_extractor(monkeypatch):
    extractor = CSharpServiceNameExtractor()
    
    # Create the XML structure directly
    root = ET.Element("Project")
    prop_group = ET.SubElement(root, "PropertyGroup")
    assembly_name = ET.SubElement(prop_group, "AssemblyName")
    assembly_name.text = "test-service"
    
    def mock_parse(file_path):
        class MockTree:
            def getroot(self):
                return root
        return MockTree()
    
    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(Path("test.csproj"))
    assert result == "test-service"

def test_name_sanitization():
    # Using JavaServiceNameExtractor as it's a concrete class
    extractor = JavaServiceNameExtractor()
    
    assert extractor._sanitize_name("testService") == "test-service"
    assert extractor._sanitize_name("test service") == "test-service"
    assert extractor._sanitize_name("test_service") == "test-service"
    assert extractor._sanitize_name("test@service!") == "testservice"
    assert extractor._sanitize_name("") == ""
    assert extractor._sanitize_name("TestService_NAME") == "test-service-name"

def test_error_handling(monkeypatch):
    java_extractor = JavaServiceNameExtractor()
    js_extractor = JavaScriptServiceNameExtractor()
    python_extractor = PythonServiceNameExtractor()
    csharp_extractor = CSharpServiceNameExtractor()
    
    # Test Java extractor with invalid XML
    def mock_parse_error(file_path):
        raise ET.ParseError()
    
    class MockPath:
        @property
        def name(self):
            return "fallback-name"
    
    monkeypatch.setattr(ET, "parse", mock_parse_error)
    monkeypatch.setattr(Path, "parent", lambda _: MockPath())
    
    result = java_extractor.extract(Path("/mock/path/pom.xml"))
    assert result == "fallback-name"
    
    # Test JavaScript extractor with invalid JSON
    def mock_open_error(file, mode='r', *args, **kwargs):
        from io import StringIO
        return StringIO("invalid json")
    
    monkeypatch.setattr("builtins.open", mock_open_error)
    monkeypatch.setattr(Path, "parent", lambda _: MockPath())
    
    result = js_extractor.extract(Path("/mock/path/package.json"))
    assert result == "fallback-name"