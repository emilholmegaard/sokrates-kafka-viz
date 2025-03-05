import os
from typing import Dict, List, Set

def clean_node_id(name: str) -> str:
    """
    Create a clean, CSS-friendly node ID

    :param name: Original name
    :return: Cleaned node ID
    """
    # Special case for hash topic
    if name == "#{":
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
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def format_topic_name(topic: str) -> str:
    """Format topic name for display."""
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


def get_template_path(template_name: str) -> str:
    """Return the full path to a template file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, 'ressources', 'templates', template_name)
    return template_path


def read_template(template_name: str) -> str:
    """Read a template file and return its contents."""
    template_path = get_template_path(template_name)
    with open(template_path, 'r') as f:
        return f.read()


def write_output_file(output_path: str, content: str) -> None:
    """Write content to an output file, creating directories if needed."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Write the content
    with open(output_path, 'w') as f:
        f.write(content)
