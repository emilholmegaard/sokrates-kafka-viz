"""Spring Cloud Stream specific analyzer."""

from pathlib import Path

from .base import BaseAnalyzer, KafkaPatterns


class SpringCloudStreamAnalyzer(BaseAnalyzer):
    """Spring Cloud Stream specific analyzer that works alongside the main Kafka analyzer."""

    def __init__(self):
        super().__init__()
        self.patterns = KafkaPatterns(
            consumers={
                # Basic patterns
                r'@StreamListener\s*\(\s*["\']([^"\']+)["\']'
            },
            producers={
                # Basic patterns
                r'@SendTo\s*\(\s*["\']([^"\']+)["\']'
            },
            ignore_patterns={r"@SpringBootTest", r"@TestConfiguration"},
        )

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Spring Cloud Stream source file or config."""
        return file_path.suffix.lower() == ".java"
