class AnalysisError(Exception):
    """Base class for analysis-related errors"""
    pass

class ConfigurationError(Exception):
    """Raised when there is an error in the configuration"""
    pass

class AnalyzerError(AnalysisError):
    """Raised when an analyzer encounters an error"""
    pass