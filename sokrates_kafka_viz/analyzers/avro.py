from typing import Dict, Any
import aiohttp
import logging

from ..core.analyzer import BaseAnalyzer
from ..core.config import Config
from ..core.errors import AnalyzerError

logger = logging.getLogger(__name__)

class AvroAnalyzer(BaseAnalyzer):
    async def analyze(self, config: Config) -> Dict[str, Any]:
        try:
            analyzer_config = config.get_analyzer_config('avro')
            if not analyzer_config:
                raise AnalyzerError('Avro analyzer configuration not found')
            
            schema_registry_url = analyzer_config.schema_registry
            timeout = analyzer_config.timeout_seconds
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{schema_registry_url}/subjects',
                    timeout=timeout
                ) as response:
                    if response.status != 200:
                        raise AnalyzerError(
                            f'Failed to fetch schemas: {response.status}'
                        )
                    subjects = await response.json()
                    
                    schemas = {}
                    for subject in subjects:
                        schema = await self._fetch_schema(
                            session, schema_registry_url, subject, timeout
                        )
                        schemas[subject] = schema
                    
                    return {
                        'schemas': schemas,
                        'total_count': len(schemas)
                    }
                    
        except Exception as e:
            raise AnalyzerError(f'Avro analysis failed: {str(e)}') from e
    
    async def _fetch_schema(self, session: aiohttp.ClientSession,
                          registry_url: str, subject: str,
                          timeout: int) -> Dict[str, Any]:
        async with session.get(
            f'{registry_url}/subjects/{subject}/versions/latest',
            timeout=timeout
        ) as response:
            if response.status != 200:
                logger.warning(f'Failed to fetch schema for {subject}')
                return None
            return await response.json()