# Kafka-Viz Visualization Guide

This guide explains the different visualization options available in Kafka-Viz and how to use them effectively.

## Available Visualization Types

Kafka-Viz supports several visualization types, each with its own strengths and use cases:

### 1. React Interactive (`--type react`)

The React Interactive visualization is a fully interactive, web-based visualization built with React and D3.js. It provides a rich, dynamic interface for exploring your Kafka architecture.

**Features:**
- Interactive graph with zoom, pan, and drag capabilities
- Node highlighting and selection
- Detailed sidebar with service, topic, and schema information
- Search functionality for schemas and services
- Force-directed layout with physics simulation
- Color-coded nodes and links for different entity types

**Best for:**
- Detailed exploration of complex architectures
- Presentations and demonstrations
- Deep analysis of service interactions
- Interactive documentation

**Example:**
```bash
kafka-viz visualize analysis_output.json --type react
```

### 2. Mermaid Diagram (`--type mermaid`)

The Mermaid Diagram visualization creates a clean, structured diagram using Mermaid.js. It presents a more static, organized view of your Kafka architecture.

**Features:**
- Clear, structured diagram with distinct sections
- Lightweight and fast to generate
- Compatible with Markdown documentation
- Simple and easy to understand

**Best for:**
- Documentation and reporting
- Sharing with teams unfamiliar with the system
- Quick overviews of architecture
- Embedding in other documents

**Example:**
```bash
kafka-viz visualize analysis_output.json --type mermaid
```

### 3. Simple HTML (`--type simple`)

The Simple HTML visualization provides a basic HTML view of your Kafka architecture. It's lightweight and minimal but still effective for understanding the system.

**Features:**
- Minimal dependencies
- Fast generation
- Compatible with most browsers
- Basic representation of architecture

**Best for:**
- Quick checks of analysis results
- Environments with limited resources
- Situations where simplicity is preferred
- Basic documentation

**Example:**
```bash
kafka-viz visualize analysis_output.json --type simple
```

## Using Visualizations

### Command Line Interface

To generate a visualization, use the `visualize` command with the `--type` option:

```bash
kafka-viz visualize [INPUT_FILE] --type [VISUALIZATION_TYPE]
```

If you don't specify a type, Kafka-Viz will prompt you to select one interactively.

You can also list all available visualization types:

```bash
kafka-viz visualize --list
# or
kafka-viz info
```

### Output Directory

By default, visualizations are generated in a directory called `kafka_visualization`. You can specify a different output directory with the `--output` option:

```bash
kafka-viz visualize analysis_output.json --type react --output my_visualization
```

### Viewing Visualizations

To view the generated visualization, open the HTML file in your web browser:

- React Interactive: `kafka_visualization/index.html`
- Mermaid Diagram: `kafka_visualization/kafka_architecture.html`
- Simple HTML: `kafka_visualization/simple_architecture.html`

## Tips for Effective Visualization

### React Interactive

1. **Rearrange Nodes**: Click and drag nodes to rearrange the layout
2. **Zoom and Pan**: Use the mouse wheel to zoom and drag the background to pan
3. **Select Nodes**: Click on nodes to see detailed information in the sidebar
4. **Reset View**: Use the "Reset View" button to return to the default view
5. **Highlight Schemas**: Click on schemas in the sidebar to highlight related services

### Mermaid Diagram

1. **Organization**: Services, topics, and schemas are organized into separate sections
2. **Relationships**: Arrows show the direction of data flow
3. **Colors**: Different entity types use different colors for easy identification
4. **Legend**: The legend explains the meaning of colors and shapes

### Simple HTML

1. **Structure**: The visualization is organized into services, topics, and their relationships
2. **Navigation**: Use browser search (Ctrl+F) to find specific services or topics

## Troubleshooting

### Common Issues

1. **Visualization Not Generating**
   - Check if the analysis file exists and is valid JSON
   - Ensure you have write permissions in the output directory
   - Try running with a different visualization type

2. **Browser Compatibility**
   - React Interactive works best in modern browsers (Chrome, Firefox, Edge)
   - Mermaid diagrams require JavaScript to be enabled
   - Simple HTML should work in any browser

3. **Large Architectures**
   - For very large systems, React Interactive may become slow
   - Consider filtering the analysis data before visualization
   - Mermaid may be more efficient for large architectures

### Getting Help

If you encounter issues with visualizations, check the logs for error messages:

```bash
kafka-viz visualize analysis_output.json --type react --verbose
```

For more specific troubleshooting, check the Kafka-Viz documentation or create an issue on GitHub.

## Customizing Visualizations

You can customize visualizations by:

1. **Modifying Templates**: Edit the template files in the resources directory
2. **Creating Custom Generators**: See [Extending Visualizations](extending-visualizations.md)
3. **Configuring Options**: Edit the configuration in `config.json`

## Best Practices

1. **Start Simple**: Use the Mermaid visualization for a quick overview
2. **Explore Details**: Use React Interactive for in-depth exploration
3. **Document**: Include visualizations in your project documentation
4. **Update Regularly**: Re-run analysis and visualization as your architecture evolves
5. **Combine Types**: Use different visualization types for different audiences and purposes
