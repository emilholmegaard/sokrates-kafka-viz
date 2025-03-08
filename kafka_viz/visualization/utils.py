"""
Utility functions for visualization generators.
"""

import json
import logging
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Resource paths
_RESOURCE_DIRS = [
    Path(__file__).parent / "resources",
]


def find_resource_file(file_path: Union[str, Path]) -> Optional[Path]:
    """Find a resource file in any of the resource directories.

    Args:
        file_path: Path to the resource file, relative to resource dir

    Returns:
        Path: Full path to the resource file or None if not found
    """
    path_obj = Path(file_path)

    # Try each resource directory
    for base_dir in _RESOURCE_DIRS:
        full_path = base_dir / path_obj
        if full_path.exists():
            logger.debug(f"Found resource at {full_path}")
            return full_path

    logger.warning(f"Resource file not found: {file_path}")
    return None


def load_template(vis_type: str, template_name: str) -> str:
    """Load a template file for the specified visualization type.

    Args:
        vis_type: Visualization type (folder name)
        template_name: Name of the template file

    Returns:
        str: Content of the template file

    Raises:
        FileNotFoundError: If the template cannot be found
    """
    template_path = find_resource_file(Path("templates") / vis_type / template_name)

    if not template_path:
        # Try a direct path approach as fallback
        direct_path = (
            Path(__file__).parent / "resources" / "templates" / vis_type / template_name
        )
        if direct_path.exists():
            template_path = direct_path
        else:
            raise FileNotFoundError(
                f"Template file not found: {template_name} for {vis_type}"
            )

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        logger.debug(f"Loaded template {template_name} for {vis_type}")
        return content


def load_config() -> Dict[str, Any]:
    """Load visualization configuration.

    Returns:
        dict: Visualization configuration
    """
    config_path = find_resource_file("config.json")

    if config_path:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}")

    # Return default config if loading fails
    return {
        "visualizations": {
            "react": {
                "name": "React Interactive",
                "description": "Interactive D3.js visualization with React UI",
                "enabled": True,
            },
            "mermaid": {
                "name": "Mermaid Diagram",
                "description": "Simple Mermaid.js flowchart diagram",
                "enabled": True,
            },
            "simple": {
                "name": "Simple HTML",
                "description": "Basic HTML visualization",
                "enabled": True,
            },
        }
    }


def write_file(output_dir: Path, filename: str, content: str) -> None:
    """Write content to a file, creating directories if needed.

    Args:
        output_dir: Directory where to write the file
        filename: Name of the file to write
        content: Content to write to the file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Write the file
    file_path = output_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.debug(f"Wrote file to {file_path}")


def ensure_templates_exist(
    vis_type: str, required_templates: List[str]
) -> Tuple[bool, Dict[str, str]]:
    """Ensure that all required templates exist and are loaded.

    Args:
        vis_type: Visualization type (folder name)
        required_templates: List of template filenames to check and load

    Returns:
        Tuple[bool, Dict[str, str]]: (success, {template_name: content})
    """
    template_contents = {}
    success = True

    for template_name in required_templates:
        try:
            content = load_template(vis_type, template_name)
            template_contents[template_name] = content
        except Exception as e:
            logger.error(f"Failed to load template {template_name} for {vis_type}: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                traceback.print_exc()
            success = False

    return success, template_contents


def clean_node_id(topic: str) -> str:
    """Create safe node ID by replacing invalid characters.

    Args:
        topic: Topic name to clean

    Returns:
        str: Safe node ID
    """
    # Special case for hash topic
    if topic == "#{":
        return "topic_hash"

    replacements = {
        "${": "",
        "}": "",
        "-": "_",
        ".": "_",
        "#": "hash",
        "@": "at",
        " ": "_",
        ":": "_",
        "/": "_",
        "\\": "_",
        "{": "",  # Add explicit handling for curly braces
        "}": "",
    }
    result = topic
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def format_topic_name(topic: str) -> str:
    """Format topic name for display.

    Args:
        topic: Topic name to format

    Returns:
        str: Formatted topic name for display
    """
    if topic == "#{":
        return "hash_topic"
    if topic == "M" or topic == "topic":
        return topic

    if "kafka.streams" in topic:
        parts = topic.replace("${", "").replace("}", "").split(".")
        meaningful_part = parts[-1]
        if meaningful_part == "target-topic":
            meaningful_part = "target"
        return f"kafka.streams...{meaningful_part}"

    if topic.startswith("app"):
        parts = topic.split(".")
        if "event" in parts:
            event_idx = parts.index("event")
            if event_idx + 1 < len(parts):
                return f"app...{parts[event_idx+1]}"
        return f"app...{parts[-1]}"

    if topic.startswith("${config"):
        parts = topic.replace("${", "").replace("}", "").split(".")
        return f"config.kafka...{parts[-1]}"

    return topic


# Functions below are kept for backward compatibility


def get_available_visualizations() -> Dict[str, Dict[str, Any]]:
    """Get available visualization options.

    Returns:
        dict: Available visualization options
    """
    from .factory import visualization_factory

    return visualization_factory.get_available_generators()


def get_generator_by_name(name: str):
    """Get a visualization generator class by name.

    Args:
        name: Name of the generator

    Returns:
        BaseGenerator: Generator instance or None if not found
    """
    from .factory import visualization_factory

    return visualization_factory.create_generator(name)
