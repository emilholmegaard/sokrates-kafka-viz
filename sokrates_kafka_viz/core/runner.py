from typing import List, Dict, Any
from pathlib import Path
import logging
from contextlib import asynccontextmanager

from .analyzer import BaseAnalyzer
from .config import Config
from .errors import AnalysisError

logger = logging.getLogger(__name__)

class AnalysisResult:
    def __init__(self):
        self.data = {}
        self.errors = []
    
    def add_result(self, analyzer_name: str, result: Any):
        self.data[analyzer_name] = result
    
    def add_error(self, analyzer_name: str, error: Exception):
        self.errors.append({
            'analyzer': analyzer_name,
            'error': str(error),
            'type': type(error).__name__
        })

class AnalysisRunner:
    def __init__(self, config: Config):
        self.config = config
        self.analyzers: List[BaseAnalyzer] = []
    
    def register_analyzer(self, analyzer: BaseAnalyzer):
        self.analyzers.append(analyzer)
    
    @asynccontextmanager
    async def _run_analyzer(self, analyzer: BaseAnalyzer, result: AnalysisResult):
        analyzer_name = analyzer.__class__.__name__
        try:
            logger.info(f'Starting analyzer: {analyzer_name}')
            yield
            logger.info(f'Completed analyzer: {analyzer_name}')
        except Exception as e:
            logger.error(f'Error in analyzer {analyzer_name}: {str(e)}')
            result.add_error(analyzer_name, e)
            raise AnalysisError(f'Analyzer {analyzer_name} failed: {str(e)}') from e
    
    async def run(self) -> AnalysisResult:
        result = AnalysisResult()
        
        for analyzer in self.analyzers:
            if not analyzer.is_enabled(self.config):
                logger.info(f'Skipping disabled analyzer: {analyzer.__class__.__name__}')
                continue
                
            async with self._run_analyzer(analyzer, result):
                analyzer_result = await analyzer.analyze(self.config)
                result.add_result(analyzer.__class__.__name__, analyzer_result)
        
        return result