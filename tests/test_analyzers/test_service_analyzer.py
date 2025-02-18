def test_analyze_java_service(
    service_analyzer, mock_service, mock_result, monkeypatch
):
    """Test Java service dependency analysis."""
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>org.springframework.cloud</groupId>
                <artifactId>spring-cloud-starter</artifactId>
            </dependency>
        </dependencies>
    </project>"""

    application_properties = """auth-service.url=http://auth-service:8080
database-service.url=http://database-service:8080"""

    def mock_exists(self):
        return self.name in ["pom.xml", "application.properties"]

    def mock_read_text(self):
        if self.name == "pom.xml":
            return pom_content
        if self.name == "application.properties":
            return application_properties
        return ""

    monkeypatch.setattr(Path, "exists", mock_exists)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)

    assert len(mock_result.service_relationships) == 2
    relationships = {r.target for r in mock_result.service_relationships}
    assert "auth-service" in relationships
    assert "database-service" in relationships
    assert all(r.type == "spring-cloud" for r in mock_result.service_relationships)