"""
React-based Kafka visualization module.

This module provides the KafkaViz generator class for visualizing Kafka communication
patterns using React and D3.js.
"""

import datetime  # Add this import
import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple, TypedDict

from .base import BaseGenerator
from .utils import ensure_templates_exist, write_file

logger = logging.getLogger(__name__)

# Required template files
REQUIRED_TEMPLATES = ["app.js", "simulation.worker.js", "styles.css", "index.html"]


# Define TypedDict classes for better type safety
class SchemaInfo(TypedDict):
    type: str
    namespace: str
    services: List[str]


class TopicInfo(TypedDict):
    producers: List[str]
    consumers: List[str]


class KafkaData(TypedDict):
    topics: Dict[str, TopicInfo]
    schemas: Dict[str, SchemaInfo]


class KafkaViz(BaseGenerator):
    """React-based interactive Kafka visualization."""

    def __init__(self):
        super().__init__()
        self.name = "React Interactive"
        self.description = "Interactive D3.js visualization with React UI"
        self.output_filename = "index.html"

    def parse_kafka_data(self, data: Dict) -> Dict:
        """Parse the JSON file and extract Kafka communication data.

        Args:
            data: The input data structure containing service information

        Returns:
            dict: Extracted service data

        Raises:
            SystemExit: If the data cannot be parsed
        """
        try:
            # Handle different potential structures of the input JSON
            if "services" in data:
                logger.debug(
                    f"Found 'services' key with {len(data['services'])} services"
                )
                return data["services"]

            elif isinstance(data, dict) and all(
                isinstance(data[k], dict) for k in data
            ):
                # If the JSON is just a dictionary of services directly
                logger.debug(
                    f"Assuming direct service dictionary with {len(data)} services"
                )
                return data

            else:
                logger.error("Could not identify services structure in the JSON file")

        except Exception as e:
            logger.error(f"Error reading or parsing file: {e}")
        return data

    def extract_kafka_communication(self, services: Dict[str, Any]) -> KafkaData:
        """Extract Kafka communication patterns from the services data."""
        topics: Dict[str, TopicInfo] = defaultdict(
            lambda: {"producers": [], "consumers": []}
        )
        schemas: Dict[str, SchemaInfo] = {}

        for service_name, service_data in services.items():
            self._process_service(service_name, service_data, topics, schemas)

        return {"topics": topics, "schemas": schemas}

    def _process_service(
        self,
        service_name: str,
        service_data: Any,
        topics: Dict[str, TopicInfo],
        schemas: Dict[str, SchemaInfo],
    ) -> None:
        """Process a single service to extract topics and schemas.

        Args:
            service_name: Name of the service
            service_data: Service data
            topics: Dictionary to populate with topic information
            schemas: Dictionary to populate with schema information
        """
        # Skip non-dict service data or empty services
        if not isinstance(service_data, dict):
            logger.debug(f"Service {service_name} is not a dict, skipping")
            return

        # Process topics if they exist
        if "topics" in service_data and isinstance(service_data["topics"], dict):
            self._process_topics(service_name, service_data["topics"], topics)

        # Collect schema information
        if "schemas" in service_data and isinstance(service_data["schemas"], dict):
            self._process_schemas(service_name, service_data["schemas"], schemas)

    def _process_topics(
        self,
        service_name: str,
        topics_data: Dict[str, Any],
        topics: Dict[str, TopicInfo],
    ) -> None:
        """Process topics for a service."""
        for topic_name, topic_info in topics_data.items():
            if not isinstance(topic_info, dict):
                logger.debug(f"Topic {topic_name} info is not a dict, skipping")
                continue

            self._add_to_collection(
                "producers", topic_name, topic_info, topics, service_name
            )
            self._add_to_collection(
                "consumers", topic_name, topic_info, topics, service_name
            )

    def _process_schemas(
        self,
        service_name: str,
        schemas_data: Dict[str, Any],
        schemas: Dict[str, SchemaInfo],
    ) -> None:
        """Process schemas for a service.

        Args:
            service_name: Name of the service
            schemas_data: Schemas data for the service
            schemas: Dictionary to populate with schema information
        """
        for schema_name, schema_info in schemas_data.items():
            # Skip if schema_info is not a dict
            if not isinstance(schema_info, dict):
                logger.debug(f"Schema {schema_name} info is not a dict, skipping")
                continue

            if schema_name not in schemas:
                schemas[schema_name] = {
                    "type": schema_info.get("type", "unknown"),
                    "namespace": schema_info.get("namespace", ""),
                    "services": [],
                }
            schemas[schema_name]["services"].append(service_name)
            logger.debug(f"Added service {service_name} to schema {schema_name}")

    def _add_to_collection(
        self,
        collection_name: str,
        item_name: str,
        item_data: Any,
        target_dict: Dict[str, TopicInfo],
        source_service: str,
    ) -> None:
        """Add items to a collection (producers/consumers) for a topic.

        Args:
            collection_name: Name of collection ("producers" or "consumers")
            item_name: Name of the topic
            item_data: Data containing the collection
            target_dict: Dictionary to update
            source_service: Service name to add
        """
        if collection_name in item_data and isinstance(
            item_data[collection_name], list
        ):
            for item in item_data[collection_name]:
                if item:  # Skip empty values
                    if collection_name == "producers":
                        target_dict[item_name]["producers"].append(source_service)
                    elif collection_name == "consumers":
                        target_dict[item_name]["consumers"].append(source_service)
                    logger.debug(
                        f"Added {collection_name[:-1]} {source_service} to topic {item_name}"
                    )

    def generate_visualization_data(
        self, services: Dict[str, Any], kafka_data: KafkaData
    ) -> Dict[str, Any]:
        """Generate the data structure for visualization.

        Args:
            services: Dictionary of service data
            kafka_data: Extracted Kafka communication data

        Returns:
            dict: Structured data for visualization
        """
        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        # Add service nodes
        service_index: Dict[str, int] = {}
        nodes, service_index = self._create_service_nodes(services)

        # Add topic nodes and create links
        nodes, links = self._create_topic_nodes_and_links(
            kafka_data, nodes, service_index
        )

        # Create schema data
        schemas = self._create_schema_data(kafka_data)

        # Validate visualization data
        if not nodes:
            logger.warning("No nodes generated in visualization data!")
        if not links:
            logger.warning("No links generated in visualization data!")

        return {"nodes": nodes, "links": links, "schemas": schemas}

    def _create_service_nodes(
        self, services: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Create service nodes for the visualization.

        Args:
            services: Dictionary of service data

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, int]]: List of nodes and service index
        """
        nodes = []
        service_index = {}
        idx = 0

        for service_name in services:
            service_index[service_name] = idx
            nodes.append(
                self._create_node(
                    id=idx,
                    name=service_name,
                    node_type="service",
                    extra_data={
                        "language": services[service_name].get("language", "unknown")
                    },
                )
            )
            idx += 1

        logger.debug(f"Added {len(service_index)} service nodes")
        return nodes, service_index

    def _create_topic_nodes_and_links(
        self,
        kafka_data: KafkaData,
        nodes: List[Dict[str, Any]],
        service_index: Dict[str, int],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create topic nodes and links between services and topics.

        Args:
            kafka_data: Extracted Kafka communication data
            nodes: Existing list of nodes
            service_index: Dictionary mapping service names to node IDs

        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: Updated nodes and links
        """
        links = []
        topic_index = {}
        idx = len(nodes)

        # Add topic nodes
        for topic_name in kafka_data["topics"]:
            topic_index[topic_name] = idx
            nodes.append(
                self._create_node(
                    id=idx,
                    name=topic_name,
                    node_type="topic",
                    extra_data={
                        "producers": kafka_data["topics"][topic_name]["producers"],
                        "consumers": kafka_data["topics"][topic_name]["consumers"],
                    },
                )
            )
            idx += 1

        logger.debug(f"Added {len(topic_index)} topic nodes")

        # Create links for producer → topic and topic → consumer
        for topic_name, topic_data in kafka_data["topics"].items():
            topic_id = topic_index[topic_name]

            # Producer → Topic links
            for producer in topic_data["producers"]:
                if producer in service_index:
                    links.append(
                        {
                            "source": service_index[producer],
                            "target": topic_id,
                            "type": "produces",
                        }
                    )

            # Topic → Consumer links
            for consumer in topic_data["consumers"]:
                if consumer in service_index:
                    links.append(
                        {
                            "source": topic_id,
                            "target": service_index[consumer],
                            "type": "consumes",
                        }
                    )

        logger.debug(f"Created {len(links)} links")
        return nodes, links

    def _create_schema_data(self, kafka_data: KafkaData) -> List[Dict[str, Any]]:
        """Create schema data for the visualization.

        Args:
            kafka_data: Extracted Kafka communication data

        Returns:
            List[Dict[str, Any]]: List of schema data
        """
        schemas = []
        for schema_name, schema_info in kafka_data["schemas"].items():
            # Only include schemas used by services
            if schema_info["services"]:
                schemas.append(
                    {
                        "name": schema_name,
                        "type": schema_info["type"],
                        "namespace": schema_info["namespace"],
                        "services": schema_info["services"],
                    }
                )

        logger.debug(f"Added {len(schemas)} schemas to visualization data")
        return schemas

    def generate_react_app(
        self, visualization_data: Dict[str, Any], output_dir: Path
    ) -> None:
        """Generate a React application with the visualization.

        Args:
            visualization_data: Data structure for visualization
            output_dir: Directory where to save the output files
        """
        logger.debug(f"Generating React app in {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        # Save visualization data as JavaScript file
        self._save_visualization_data(visualization_data, output_dir)

        # Generate and write HTML/CSS/JS files
        self._generate_app_files(output_dir)

        logger.info(f"React app generated in {output_dir}")

    def _save_visualization_data(
        self, visualization_data: Dict[str, Any], output_dir: Path
    ) -> None:
        """Save visualization data as a JavaScript file."""
        # Validate data structure
        if not visualization_data.get("nodes"):
            logger.error("No nodes found in visualization data")
            visualization_data["nodes"] = []

        if not visualization_data.get("links"):
            logger.error("No links found in visualization data")
            visualization_data["links"] = []

        if not visualization_data.get("schemas"):
            logger.error("No schemas found in visualization data")
            visualization_data["schemas"] = []

        # Add validation info to help debugging
        visualization_data["_debug"] = {
            "generatedAt": str(datetime.datetime.now()),
            "nodesCount": len(visualization_data["nodes"]),
            "linksCount": len(visualization_data["links"]),
            "schemasCount": len(visualization_data["schemas"]),
        }

        vis_data_js = (
            f"window.visualizationData = {json.dumps(visualization_data, indent=2)};\n"
        )
        vis_data_path = os.path.join(output_dir, "visualization-data.js")

        with open(vis_data_path, "w") as f:
            f.write(vis_data_js)

        logger.debug(f"Wrote visualization data to {vis_data_path}")

        # Log data summary
        logger.debug("Visualization data summary:")
        logger.debug(f"  - Nodes: {len(visualization_data.get('nodes', []))}")
        logger.debug(f"  - Links: {len(visualization_data.get('links', []))}")
        logger.debug(f"  - Schemas: {len(visualization_data.get('schemas', []))}")

    def _generate_app_files(self, output_dir: Path) -> None:
        """Generate and write HTML/CSS/JS files for the React app."""
        try:
            success, template_contents = ensure_templates_exist(
                "react", REQUIRED_TEMPLATES
            )

            # Updated index.html with better error handling and debugging
            index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kafka Communication Visualization</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div id="root">
        <div style="padding: 20px;">Loading visualization...</div>
    </div>
    
    <!-- Add error boundary -->
    <div id="error-container" style="display:none; color:red; padding:20px;"></div>

    <script>
        window.addEventListener('error', function(e) {
            console.error('Global error:', e);
            document.getElementById('error-container').style.display = 'block';
            document.getElementById('error-container').innerHTML = 
                `<h3>Error Loading Visualization</h3><pre>${e.message}</pre>`;
        });

        // Debug helper
        function checkDependencies() {
            console.log('Checking dependencies...');
            console.log('React:', typeof React !== 'undefined');
            console.log('ReactDOM:', typeof ReactDOM !== 'undefined');
            console.log('d3:', typeof d3 !== 'undefined');
            console.log('Babel:', typeof Babel !== 'undefined');
            console.log('visualizationData:', typeof window.visualizationData !== 'undefined');
        }
    </script>

    <!-- Load dependencies -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.0.0/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.14.7/babel.min.js"></script>

    <!-- Check dependencies loaded -->
    <script>
        checkDependencies();
    </script>

    <!-- Load visualization data -->
    <script src="visualization-data.js"></script>
    
    <!-- Verify data loaded -->
    <script>
        console.log('Visualization data loaded:', {
            hasData: typeof window.visualizationData !== 'undefined',
            nodes: window.visualizationData?.nodes?.length,
            links: window.visualizationData?.links?.length,
            schemas: window.visualizationData?.schemas?.length
        });
    </script>

    <!-- Load app with error handling -->
    <script type="text/babel">
        try {
            // Verify React is loaded before loading app.js
            if (typeof React === 'undefined') {
                throw new Error('React not loaded');
            }
            // Load the main app
            fetch('app.js')
                .then(response => response.text())
                .then(code => {
                    try {
                        eval(Babel.transform(code, { presets: ['react'] }).code);
                    } catch (error) {
                        console.error('Error evaluating app code:', error);
                        document.getElementById('error-container').style.display = 'block';
                        document.getElementById('error-container').innerHTML = 
                            `<h3>Error Running App</h3><pre>${error.message}</pre>`;
                    }
                })
                .catch(error => {
                    console.error('Error loading app.js:', error);
                    document.getElementById('error-container').style.display = 'block';
                    document.getElementById('error-container').innerHTML = 
                        `<h3>Error Loading App</h3><pre>${error.message}</pre>`;
                });
        } catch (error) {
            console.error('Setup error:', error);
            document.getElementById('error-container').style.display = 'block';
            document.getElementById('error-container').innerHTML = 
                `<h3>Setup Error</h3><pre>${error.message}</pre>`;
        }
    </script>
</body>
</html>"""
            # Write files
            write_file(output_dir, "index.html", index_html)

            if success:
                # Write template files if successfully loaded
                write_file(output_dir, "index.html", template_contents["index.html"])
                write_file(output_dir, "styles.css", template_contents["styles.css"])
                write_file(output_dir, "app.js", template_contents["app.js"])
                write_file(
                    output_dir,
                    "simulation.worker.js",
                    template_contents["simulation.worker.js"],
                )
            else:
                # Fall back to default files if templates couldn't be loaded
                self._write_fallback_files(output_dir)

        except Exception as e:
            logger.error(f"Error generating React app: {e}")
            self._write_fallback_files(output_dir)

    def _write_fallback_files(self, output_dir: Path) -> None:
        """Write fallback CSS and JS files when templates can't be loaded.

        Args:
            output_dir: Directory where to save the files
        """
        logger.warning("Using fallback templates")

        # Load fallback templates from the resources directory
        try:
            # Try to load fallback templates
            fallback_path = Path(__file__).parent / "resources" / "fallback"

            if fallback_path.exists():
                with open(fallback_path / "styles.css", "r", encoding="utf-8") as f:
                    css = f.read()
                with open(fallback_path / "app.js", "r", encoding="utf-8") as f:
                    app_js = f.read()

                write_file(Path(output_dir), "styles.css", css)
                write_file(Path(output_dir), "app.js", app_js)
                return
        except Exception as e:
            logger.error(f"Error loading fallback templates: {e}")

        # Hard-coded fallbacks are not included here.
        # Instead, create minimal placeholders that point to the issue.
        css = """
        body { font-family: Arial, sans-serif; margin: 20px; }
        .error { color: red; background: #ffeeee; padding: 20px; border: 1px solid #ffcccc; }
        """

        app_js = """
        document.getElementById('root').innerHTML = `
            <div class="error">
                <h2>Template Loading Error</h2>
                <p>The visualization templates could not be loaded.</p>
                <p>Please ensure that the template files exist
                 in the resources/templates/react directory:</p>
                <ul>
                    <li>app.js</li>
                    <li>styles.css</li>
                </ul>
                <p>Check the console for more information.</p>
            </div>
        `;
        console.error('Failed to load visualization templates.');
        """

        write_file(Path(output_dir), "styles.css", css)
        write_file(Path(output_dir), "app.js", app_js)

    def generate_html(self, data: dict) -> str:
        """Generate HTML for the visualization.

        This method is required by BaseGenerator, but for this visualization
        we create a full app instead of a single HTML file.

        Args:
            data: The parsed Kafka analysis data

        Returns:
            str: Empty string as files are generated separately
        """
        return ""

    def generate_output(self, data: dict, file_path: Path) -> None:
        """Generate the visualization output.

        Args:
            data: The parsed Kafka analysis data
            file_path: Path where to save the visualization files
        """
        try:
            # Parse the JSON file
            services = self.parse_kafka_data(data)

            # Extract Kafka communication data
            kafka_data = self.extract_kafka_communication(services)

            # Generate the visualization data
            visualization_data = self.generate_visualization_data(services, kafka_data)

            # Generate the React app
            self.generate_react_app(visualization_data, file_path)

            logger.info("Kafka communication visualization generated successfully!")
            logger.info(f"Visualization generated at {file_path}")

        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            raise

    def _create_node(
        self, id: int, name: str, node_type: str, extra_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a node with consistent structure.

        Args:
            id: Node ID
            name: Node name
            node_type: Type of node ("service" or "topic")
            extra_data: Additional node data
        """
        node = {
            "id": id,
            "name": name,
            "type": node_type,
        }
        if extra_data:
            node.update(extra_data)
        return node
