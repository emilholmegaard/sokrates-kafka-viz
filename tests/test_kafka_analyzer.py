import unittest
from pathlib import Path
from kafka_viz.analyzers.kafka_analyzer import KafkaAnalyzer
from kafka_viz.models.service import Service

class TestKafkaAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = KafkaAnalyzer()
        self.test_data_dir = Path(__file__).parent / 'test_data'
        
    def test_java_patterns(self):
        java_service = Service(
            name="java-service",
            source_files=[self.test_data_dir / 'java_service' / 'KafkaPatternTest.java']
        )
        
        topics = self.analyzer.analyze_service(java_service)
        
        # Test producer patterns
        self.assertIn('producer-topic-1', topics)
        self.assertIn('response-topic', topics)
        self.assertIn('output-topic', topics)
        self.assertIn('template-topic', topics)
        self.assertIn('custom-topic', topics)
        self.assertIn('direct-topic', topics)
        self.assertIn('record-topic', topics)
        self.assertIn('publish-topic', topics)
        self.assertIn('explicit-topic', topics)
        self.assertIn('message-topic', topics)
        self.assertIn('kafka-topic', topics)
        
        # Test consumer patterns
        self.assertIn('listener-topic-1', topics)
        self.assertIn('listener-topic.*', topics)
        self.assertIn('stream-topic', topics)
        self.assertIn('input-topic', topics)
        self.assertIn('singleton-topic', topics)
        self.assertIn('array-topic-1', topics)
        self.assertIn('array-topic-2', topics)
        self.assertIn('set-topic', topics)
        self.assertIn('list-topic', topics)
        self.assertIn('config-topic', topics)
        
    def test_python_patterns(self):
        python_service = Service(
            name="python-service",
            source_files=[self.test_data_dir / 'python_service' / 'kafka_pattern_test.py']
        )
        
        topics = self.analyzer.analyze_service(python_service)
        
        # Test constant/variable patterns
        self.assertIn('constant-topic', topics)
        self.assertIn('variable-topic', topics)
        self.assertIn('config-topic', topics)
        self.assertIn('consumer-topic', topics)
        
        # Test producer patterns
        self.assertIn('producer-config-topic', topics)
        self.assertIn('direct-topic', topics)
        self.assertIn('produce-topic', topics)
        self.assertIn('confluent-topic', topics)
        
        # Test consumer patterns
        self.assertIn('consumer-config-topic', topics)
        self.assertIn('decorator-topic', topics)
        self.assertIn('consumer-decorator-topic', topics)
        self.assertIn('subscribe-topic', topics)
        self.assertIn('pattern-topic.*', topics)
        
    def test_csharp_patterns(self):
        csharp_service = Service(
            name="csharp-service",
            source_files=[self.test_data_dir / 'csharp_service' / 'KafkaPatternTest.cs']
        )
        
        topics = self.analyzer.analyze_service(csharp_service)
        
        # Test attribute patterns
        self.assertIn('attribute-topic', topics)
        
        # Test config patterns
        self.assertIn('producer-config-topic', topics)
        self.assertIn('consumer-config-topic', topics)
        
        # Test producer patterns
        self.assertIn('direct-topic', topics)
        self.assertIn('sync-topic', topics)
        self.assertIn('builder-topic', topics)
        self.assertIn('with-topic', topics)
        self.assertIn('message-topic', topics)
        self.assertIn('send-topic', topics)
        
        # Test consumer patterns
        self.assertIn('listener-topic', topics)
        self.assertIn('array-topic', topics)
        self.assertIn('async-topic', topics)
        
        # Test settings patterns
        self.assertIn('settings-topic', topics)

if __name__ == '__main__':
    unittest.main()
