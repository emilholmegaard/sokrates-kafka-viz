def test_java_service_name_extractor_fallback(monkeypatch):
    extractor = JavaServiceNameExtractor()
    
    class MockParent:
        name = "fallback-name"
    
    def mock_parse(file_path):
        raise ET.ParseError()

    mock_path = Path("/mock/path/pom.xml")
    monkeypatch.setattr(mock_path, "parent", MockParent())
    monkeypatch.setattr(ET, "parse", mock_parse)
    
    result = extractor.extract(mock_path)
    assert result == "fallback-name"