import pytest
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock
import xml.etree.ElementTree as ET

from kafka_viz.analyzers.service_name_extractors import (
    JavaServiceNameExtractor,
    JavaScriptServiceNameExtractor,
    PythonServiceNameExtractor,
    CSharpServiceNameExtractor,
)

@pytest.fixture
def mock_path():
    return Path("/mock/path")

def test_java_service_name_extractor_pom_xml():
    extractor = JavaServiceNameExtractor()
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <artifactId>test-service</artifactId>
        <name>Test Service Name</name>
    </project>"""
    
    with patch("pathlib.Path.open", mock_open(read_data=pom_content)), \
         patch("xml.etree.ElementTree.parse") as mock_parse:
        
        # Mock the XML parsing
        mock_tree = MagicMock()
        mock_root = ET.fromstring(pom_content)
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree
        
        result = extractor.extract(Path("pom.xml"))
        assert result == "test-service"

def test_java_service_name_extractor_gradle():
    extractor = JavaServiceNameExtractor()
    gradle_content = """
    rootProject.name = 'test-service'
    archivesBaseName = 'alternate-name'
    """
    
    with patch("pathlib.Path.read_text") as mock_read_text, \
         patch("pathlib.Path.exists") as mock_exists:
        
        mock_read_text.return_value = gradle_content
        mock_exists.return_value = False
        
        result = extractor.extract(Path("build.gradle"))
        assert result == "test-service"

def test_javascript_service_name_extractor():
    extractor = JavaScriptServiceNameExtractor()
    package_json_content = """{
        "name": "@scope/test-service",
        "version": "1.0.0"
    }"""
    
    with patch("builtins.open", mock_open(read_data=package_json_content)):
        result = extractor.extract(Path("package.json"))
        assert result == "test-service"

def test_javascript_service_name_extractor_fallback():
    extractor = JavaScriptServiceNameExtractor()
    
    with patch("builtins.open", mock_open(read_data="{}")), \
         patch.object(Path, "parent") as mock_parent:
        
        mock_parent.name = "fallback-service"
        result = extractor.extract(Path("package.json"))
        assert result == "fallback-service"

def test_python_service_name_extractor_setup_py():
    extractor = PythonServiceNameExtractor()
    setup_py_content = """
    from setuptools import setup

    setup(
        name='test-service',
        version='1.0.0'
    )
    """
    
    with patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = setup_py_content
        result = extractor.extract(Path("setup.py"))
        assert result == "test-service"

def test_python_service_name_extractor_pyproject_toml():
    extractor = PythonServiceNameExtractor()
    pyproject_content = """
    [project]
    name = "test-service"
    version = "1.0.0"
    """
    
    with patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.return_value = pyproject_content
        result = extractor.extract(Path("pyproject.toml"))
        assert result == "test-service"

def test_python_service_name_extractor_requirements_txt():
    extractor = PythonServiceNameExtractor()
    
    with patch.object(Path, "parent") as mock_parent:
        mock_parent.name = "test-service"
        result = extractor.extract(Path("requirements.txt"))
        assert result == "test-service"

def test_csharp_service_name_extractor():
    extractor = CSharpServiceNameExtractor()
    csproj_content = """<?xml version="1.0" encoding="utf-8"?>
    <Project Sdk="Microsoft.NET.Sdk">
        <PropertyGroup>
            <AssemblyName>TestService</AssemblyName>
            <RootNamespace>Test.Service</RootNamespace>
        </PropertyGroup>
    </Project>"""
    
    with patch("pathlib.Path.open", mock_open(read_data=csproj_content)), \
         patch("xml.etree.ElementTree.parse") as mock_parse:
        
        # Mock the XML parsing
        mock_tree = MagicMock()
        mock_root = ET.fromstring(csproj_content)
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree
        
        result = extractor.extract(Path("test.csproj"))
        assert result == "test-service"

def test_csharp_service_name_extractor_fallback():
    extractor = CSharpServiceNameExtractor()
    
    with patch("xml.etree.ElementTree.parse") as mock_parse:
        mock_parse.side_effect = Exception("Parse error")
        result = extractor.extract(Path("test-service.csproj"))
        assert result == "test-service"

def test_name_sanitization():
    extractor = JavaServiceNameExtractor()  # Any extractor would work
    
    # Test camelCase to kebab-case
    assert extractor._sanitize_name("testService") == "test-service"
    
    # Test spaces and underscores
    assert extractor._sanitize_name("test service") == "test-service"
    assert extractor._sanitize_name("test_service") == "test-service"
    
    # Test invalid characters
    assert extractor._sanitize_name("test@service!") == "testservice"
    
    # Test empty string
    assert extractor._sanitize_name("") == ""
    
    # Test mixed cases
    assert extractor._sanitize_name("TestService_NAME") == "test-service-name"

def test_error_handling():
    java_extractor = JavaServiceNameExtractor()
    js_extractor = JavaScriptServiceNameExtractor()
    python_extractor = PythonServiceNameExtractor()
    csharp_extractor = CSharpServiceNameExtractor()
    
    # Test Java extractor with invalid XML
    with patch("xml.etree.ElementTree.parse") as mock_parse:
        mock_parse.side_effect = ET.ParseError("Invalid XML")
        result = java_extractor.extract(Path("pom.xml"))
        assert result is None
    
    # Test JavaScript extractor with invalid JSON
    with patch("builtins.open", mock_open(read_data="invalid json")):
        result = js_extractor.extract(Path("package.json"))
        assert result is not None  # Should fall back to directory name
    
    # Test Python extractor with invalid file
    with patch("pathlib.Path.read_text") as mock_read_text:
        mock_read_text.side_effect = Exception("Read error")
        result = python_extractor.extract(Path("setup.py"))
        assert result is None
    
    # Test C# extractor with invalid XML
    with patch("xml.etree.ElementTree.parse") as mock_parse:
        mock_parse.side_effect = Exception("Parse error")
        result = csharp_extractor.extract(Path("test.csproj"))
        assert result == "test"  # Should fall back to file stem