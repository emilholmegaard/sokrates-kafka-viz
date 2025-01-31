import logging
import sys

def configure_logging(verbose: bool = False):
    """Configure logging for the application.
    
    Args:
        verbose (bool): If True, set logging level to DEBUG. Otherwise, set to INFO.
    """
    # Create logger
    logger = logging.getLogger('kafka_viz')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create console handler and set level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger
