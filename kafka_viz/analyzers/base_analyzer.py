from typing import Any, Dict


class BaseAnalyzer:
    """Base class for all analyzers."""

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the analysis.

        Returns:
            Dict containing debug information. Should be overridden by subclasses.
        """
        return {}
