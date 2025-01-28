import logging
from typing import Optional
from .config import Config

def setup_logging(config: Config, log_file: Optional[str] = None):
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            *([] if not log_file else [logging.FileHandler(log_file)])
        ]
    )