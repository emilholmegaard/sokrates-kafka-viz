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

    application_properties = """
    auth-service.url=http://auth-service:8080
    database-service.url=http://database-service:8080
    """

    # Mock file existence and content reading
    def mock_read_text(self):
        if self.name == "pom.xml":
            return pom_content
        return application_properties

    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    service_analyzer._analyze_java_service(mock_service, mock_result)

    # Verify relationships were created
    assert len(mock_result.service_relationships) == 2
    relationships = {r.target: r for r in mock_result.service_relationships}
    assert "auth-service" in relationships
    assert "database-service" in relationships
    assert all(r.type == "spring-cloud" for r in mock_result.service_relationships)