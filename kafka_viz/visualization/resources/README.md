# Visualization Resources

This directory contains static resources and templates for visualization generators.

## Directory Structure

```
resources/
├── config.json              # Configuration for visualization options
└── templates/               # Templates for different visualization types
    ├── mermaid/             # Templates for Mermaid diagrams
    │   └── mermaid.html     # HTML template for Mermaid diagrams
    ├── react/               # Templates for React visualizations
    │   ├── app.js           # React application JavaScript
    │   ├── index.html       # HTML template for React app
    │   └── styles.css       # CSS styles for React app
    └── [other_types]/       # Templates for other visualization types
```

## Adding New Visualization Types

To add a new visualization type:

1. Create a new directory under `templates/` for your visualization type
2. Add all necessary template files for your visualization
3. Create a new visualization generator class that extends `BaseGenerator`
4. Register your generator in the `VisualizationFactory`

## Template Usage

Templates can use Python's string formatting with curly braces `{}`. For example:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
</head>
<body>
    {content}
</body>
</html>
```

## Configuration

The `config.json` file controls which visualization types are available and their metadata:

```json
{
  "visualizations": {
    "react": {
      "name": "React Interactive",
      "description": "Interactive D3.js visualization with React UI",
      "enabled": true
    },
    "mermaid": {
      "name": "Mermaid Diagram",
      "description": "Simple Mermaid.js flowchart diagram",
      "enabled": true
    }
  }
}
```

To disable a visualization type, set `"enabled": false` in the config.
