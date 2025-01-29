import unittest
from pathlib import Path
from kafka_viz.analyzers.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models.service import Service

class TestKafkaAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = KafkaAnalyzer()
        self.test_data_dir = Path(__file__).parent / 'test_data'
        
    def test_java_patterns(self):
        service_path = self.test_data_dir / 'java_service'
        java_service = Service(
            name="java-service",
            path=service_path,
            language="java"
        )
        
        topics = self.analyzer.analyze_service(java_service)
        
        # Test producer patterns
        self.assertIn('producer-topic-1', topics)
        self.assertIn('response-topic', topics)
        # ... rest of assertions unchanged ...
        
    def test_python_patterns(self):
        service_path = self.test_data_dir / 'python_service'
        python_service = Service(
            name="python-service",
            path=service_path,
            language="python"
        )
        
        topics = self.analyzer.analyze_service(python_service)
        
        # Test constant/variable patterns
        self.assertIn('constant-topic', topics)
        # ... rest of assertions unchanged ...
        
    def test_csharp_patterns(self):
        service_path = self.test_data_dir / 'csharp_service'
        csharp_service = Service(
            name="csharp-service",
            path=service_path,
            language="csharp"
        )
        
        topics = self.analyzer.analyze_service(csharp_service)
        
        # Test attribute patterns
        self.assertIn('attribute-topic', topics)
        # ... rest of assertions unchanged ...

if __name__ == '__main__':
    unittest.main()
