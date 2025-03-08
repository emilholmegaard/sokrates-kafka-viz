import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from .base import BaseGenerator
from .utils import load_template, write_file


class KafkaViz(BaseGenerator):
    """React-based interactive Kafka visualization."""
    
    def __init__(self):
        super().__init__()
        self.name = "React Interactive"
        self.description = "Interactive D3.js visualization with React UI"
        self.output_filename = "index.html"
        
    def parse_kafka_data(self, data: dict) -> dict:
        """Parse the JSON file and extract Kafka communication data."""
        try:
            # Handle different potential structures of the input JSON
            if "services" in data:
                return data["services"]
            elif isinstance(data, dict) and all(
                isinstance(data[k], dict) for k in data
            ):
                # If the JSON is just a dictionary of services directly
                return data
            else:
                print("Error: Could not identify services structure in the JSON file")
                sys.exit(1)
        except Exception as e:
            print(f"Error reading or parsing file: {e}")
            sys.exit(1)

    def extract_kafka_communication(self, services) -> dict:
        """Extract Kafka communication patterns from the services data."""
        topics = defaultdict(lambda: {"producers": set(), "consumers": set()})
        schemas = {}

        # Extract topics and their producers/consumers
        for service_name, service_data in services.items():
            # Skip non-dict service data or empty services
            if not isinstance(service_data, dict):
                continue

            # Process topics if they exist
            if "topics" in service_data and isinstance(service_data["topics"], dict):
                for topic_name, topic_info in service_data["topics"].items():
                    # Skip if topic_info is not a dict
                    if not isinstance(topic_info, dict):
                        continue

                    # Add producers
                    if "producers" in topic_info and isinstance(
                        topic_info["producers"], list
                    ):
                        for producer in topic_info["producers"]:
                            if producer:  # Skip empty values
                                topics[topic_name]["producers"].add(producer)

                    # Add consumers
                    if "consumers" in topic_info and isinstance(
                        topic_info["consumers"], list
                    ):
                        for consumer in topic_info["consumers"]:
                            if consumer:  # Skip empty values
                                topics[topic_name]["consumers"].add(consumer)

            # Collect schema information
            if "schemas" in service_data and isinstance(service_data["schemas"], dict):
                for schema_name, schema_info in service_data["schemas"].items():
                    # Skip if schema_info is not a dict
                    if not isinstance(schema_info, dict):
                        continue

                    if schema_name not in schemas:
                        schemas[schema_name] = {
                            "type": schema_info.get("type", "unknown"),
                            "namespace": schema_info.get("namespace", ""),
                            "services": [],
                        }
                    schemas[schema_name]["services"].append(service_name)

        # Convert sets to lists for JSON serialization
        for topic_name in topics:
            topics[topic_name]["producers"] = list(topics[topic_name]["producers"])
            topics[topic_name]["consumers"] = list(topics[topic_name]["consumers"])

        return {"topics": topics, "schemas": schemas}

    def generate_visualization_data(self, services, kafka_data) -> dict:
        """Generate the data structure for visualization."""
        nodes = []
        links = []

        # Add service nodes
        service_index = {}
        idx = 0
        for service_name in services:
            service_index[service_name] = idx
            nodes.append(
                {
                    "id": idx,
                    "name": service_name,
                    "type": "service",
                    "language": services[service_name].get("language", "unknown"),
                }
            )
            idx += 1

        # Add topic nodes
        topic_index = {}
        for topic_name in kafka_data["topics"]:
            topic_index[topic_name] = idx
            nodes.append(
                {
                    "id": idx,
                    "name": topic_name,
                    "type": "topic",
                    "producers": kafka_data["topics"][topic_name]["producers"],
                    "consumers": kafka_data["topics"][topic_name]["consumers"],
                }
            )
            idx += 1

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

        # Create schema data
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

        return {"nodes": nodes, "links": links, "schemas": schemas}

    def generate_react_app(self, visualization_data, output_dir):
        """Generate a React application with the visualization."""
        os.makedirs(output_dir, exist_ok=True)

        # Save visualization data as JSON
        # Important: Make the JSON available as a global variable in JavaScript
        vis_data_js = f"window.visualizationData = {json.dumps(visualization_data, indent=2)};"
        with open(os.path.join(output_dir, "visualization-data.js"), "w") as f:
            f.write(vis_data_js)

        try:
            # Get template content
            index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kafka Communication Visualization</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div id="root"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.0.0/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.14.7/babel.min.js"></script>
    <!-- Load the data first -->
    <script src="visualization-data.js"></script>
    <!-- Then load the app -->
    <script src="app.js" type="text/babel"></script>
</body>
</html>"""

            css = load_template("react", "styles.css")
            app_js = load_template("react", "app.js")
            
            # Write files
            write_file(Path(output_dir), "index.html", index_html)
            write_file(Path(output_dir), "styles.css", css)
            write_file(Path(output_dir), "app.js", app_js)
            
        except Exception as e:
            print(f"Error loading templates: {e}")
            
            # Fallback CSS and app.js (in case templates can't be loaded)
            css = """body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

#root {
    width: 100%;
    height: 100vh;
}

.app-container {
    display: flex;
    height: 100%;
}

.graph-container {
    flex: 1;
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
    margin: 1rem;
    overflow: hidden;
}

.sidebar {
    width: 300px;
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
    margin: 1rem 1rem 1rem 0;
    padding: 1rem;
    overflow-y: auto;
}

.node-service {
    fill: #4caf50;
    stroke: #388e3c;
    stroke-width: 2px;
}

.node-topic {
    fill: #2196f3;
    stroke: #1976d2;
    stroke-width: 2px;
}

.link-produces {
    stroke: #ff5722;
    stroke-width: 2px;
}

.link-consumes {
    stroke: #9c27b0;
    stroke-width: 2px;
}

.node-text {
    font-size: 12px;
    fill: #212121;
    pointer-events: none;
}

.schema-item {
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: #f5f5f5;
    border-radius: 4px;
}

.schema-name {
    font-weight: bold;
    color: #1976d2;
}

.schema-type {
    font-style: italic;
    color: #757575;
}

.schema-namespace {
    font-size: 0.9rem;
    color: #757575;
    word-break: break-all;
}

.schema-services {
    margin-top: 0.5rem;
}

.schema-service {
    display: inline-block;
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
    padding: 0.25rem 0.5rem;
    background-color: #e0e0e0;
    border-radius: 4px;
    font-size: 0.9rem;
}

.controls {
    position: absolute;
    top: 1rem;
    left: 1rem;
    background-color: rgba(255, 255, 255, 0.8);
    padding: 0.5rem;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
}

button {
    margin-right: 0.5rem;
    padding: 0.25rem 0.5rem;
    background-color: #2196f3;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

button:hover {
    background-color: #1976d2;
}

.legend {
    position: absolute;
    bottom: 1rem;
    left: 1rem;
    background-color: rgba(255, 255, 255, 0.8);
    padding: 0.5rem;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
}

.legend-item {
    display: flex;
    align-items: center;
    margin-bottom: 0.25rem;
}

.legend-color {
    width: 16px;
    height: 16px;
    margin-right: 0.5rem;
    border-radius: 4px;
}

.legend-label {
    font-size: 12px;
}"""

            app_js = """// Access the visualization data from the global scope
// const visualizationData = window.visualizationData;
// If visualizationData is not defined, show an error message
if (!window.visualizationData) {
    document.getElementById('root').innerHTML = '<div style="color: red; padding: 20px;">Error: No visualization data found. Please regenerate the visualization.</div>';
} else {
    // Main App component
    const App = () => {
        const [selectedNode, setSelectedNode] = React.useState(null);
        const [selectedSchema, setSelectedSchema] = React.useState(null);
        const [searchTerm, setSearchTerm] = React.useState("");
        
        const filteredSchemas = window.visualizationData.schemas.filter(schema => 
            schema.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            schema.namespace.toLowerCase().includes(searchTerm.toLowerCase()) ||
            schema.services.some(service => service.toLowerCase().includes(searchTerm.toLowerCase()))
        );
        
        return (
            <div className="app-container">
                <Graph 
                    data={window.visualizationData} 
                    selectedNode={selectedNode}
                    setSelectedNode={setSelectedNode}
                    selectedSchema={selectedSchema}
                    setSelectedSchema={setSelectedSchema}
                />
                <div className="sidebar">
                    <h2>Kafka Communication Details</h2>
                    {selectedNode ? (
                        <NodeDetails node={selectedNode} data={window.visualizationData} />
                    ) : (
                        <>
                            <h3>Schemas</h3>
                            <input
                                type="text"
                                placeholder="Search schemas..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                style={{ width: '100%', marginBottom: '1rem', padding: '0.5rem' }}
                            />
                            {filteredSchemas.map((schema, index) => (
                                <div 
                                    key={index} 
                                    className="schema-item"
                                    onClick={() => setSelectedSchema(schema.name === selectedSchema ? null : schema.name)}
                                    style={{ cursor: 'pointer', backgroundColor: schema.name === selectedSchema ? '#e3f2fd' : '#f5f5f5' }}
                                >
                                    <div className="schema-name">{schema.name}</div>
                                    <div className="schema-type">{schema.type}</div>
                                    <div className="schema-namespace">{schema.namespace}</div>
                                    <div className="schema-services">
                                        {schema.services.map((service, serviceIndex) => (
                                            <span key={serviceIndex} className="schema-service">{service}</span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </>
                    )}
                </div>
            </div>
        );
    };

    // Graph component
    const Graph = ({ data, selectedNode, setSelectedNode, selectedSchema, setSelectedSchema }) => {
        const svgRef = React.useRef(null);
        const [simulation, setSimulation] = React.useState(null);
        
        // Initialize and update the D3 force simulation
        React.useEffect(() => {
            if (!data || !svgRef.current) return;
            
            const width = svgRef.current.parentElement.clientWidth;
            const height = svgRef.current.parentElement.clientHeight;
            
            // Clear SVG
            d3.select(svgRef.current).selectAll("*").remove();
            
            // Create SVG
            const svg = d3.select(svgRef.current)
                .attr("width", width)
                .attr("height", height);
                
            // Add zoom behavior
            const zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on("zoom", (event) => {
                    g.attr("transform", event.transform);
                });
                
            svg.call(zoom);
            
            const g = svg.append("g");
            
            // Create a force simulation
            const sim = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(60));
                
            setSimulation(sim);
            
            // Draw links
            const link = g.append("g")
                .selectAll("line")
                .data(data.links)
                .enter().append("line")
                .attr("class", d => `link-${d.type}`)
                .attr("marker-end", d => `url(#arrow-${d.type})`);
                
            // Add arrow markers
            svg.append("defs").selectAll("marker")
                .data(["produces", "consumes"])
                .enter().append("marker")
                .attr("id", d => `arrow-${d}`)
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 15)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("class", d => `link-${d}`);
                
            // Draw nodes
            const node = g.append("g")
                .selectAll("circle")
                .data(data.nodes)
                .enter().append("circle")
                .attr("class", d => `node-${d.type}`)
                .attr("r", d => d.type === 'service' ? 20 : 15)
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended))
                .on("click", (event, d) => {
                    event.stopPropagation();
                    setSelectedNode(d.id === selectedNode?.id ? null : d);
                });
                
            // Add node labels
            const label = g.append("g")
                .selectAll("text")
                .data(data.nodes)
                .enter().append("text")
                .attr("class", "node-text")
                .attr("text-anchor", "middle")
                .attr("dy", 30)
                .text(d => {
                    const name = d.name;
                    return name.length > 20 ? name.substring(0, 17) + '...' : name;
                });
                
            // Handle schema highlighting
            if (selectedSchema) {
                const services = data.schemas.find(s => s.name === selectedSchema)?.services || [];
                
                node.attr("opacity", d => {
                    if (d.type === 'service' && services.includes(d.name)) {
                        return 1;
                    } else if (d.type === 'topic') {
                        const producers = d.producers.filter(p => services.includes(p));
                        const consumers = d.consumers.filter(c => services.includes(c));
                        return producers.length > 0 || consumers.length > 0 ? 1 : 0.2;
                    } else {
                        return 0.2;
                    }
                });
                
                link.attr("opacity", d => {
                    const source = data.nodes.find(n => n.id === d.source.id);
                    const target = data.nodes.find(n => n.id === d.target.id);
                    
                    if (source.type === 'service' && services.includes(source.name)) {
                        return 1;
                    } else if (target.type === 'service' && services.includes(target.name)) {
                        return 1;
                    } else {
                        return 0.1;
                    }
                });
                
                label.attr("opacity", d => {
                    if (d.type === 'service' && services.includes(d.name)) {
                        return 1;
                    } else if (d.type === 'topic') {
                        const producers = d.producers.filter(p => services.includes(p));
                        const consumers = d.consumers.filter(c => services.includes(c));
                        return producers.length > 0 || consumers.length > 0 ? 1 : 0.2;
                    } else {
                        return 0.2;
                    }
                });
            } else {
                node.attr("opacity", 1);
                link.attr("opacity", 1);
                label.attr("opacity", 1);
            }
            
            // Handle selected node highlighting
            if (selectedNode) {
                node.attr("stroke-width", d => d.id === selectedNode.id ? 4 : 2);
                
                if (selectedNode.type === 'service') {
                    link.attr("stroke-width", d => {
                        const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                        const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                        return sourceId === selectedNode.id || targetId === selectedNode.id ? 4 : 2;
                    });
                } else if (selectedNode.type === 'topic') {
                    link.attr("stroke-width", d => {
                        const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
                        const targetId = typeof d.target === 'object' ? d.target.id : d.target;
                        return sourceId === selectedNode.id || targetId === selectedNode.id ? 4 : 2;
                    });
                }
            } else {
                node.attr("stroke-width", 2);
                link.attr("stroke-width", 2);
            }
            
            // Add legend
            const legend = svg.append("g")
                .attr("class", "legend")
                .attr("transform", "translate(10, 10)");
                
            const legendItems = [
                { color: "#4caf50", label: "Service" },
                { color: "#2196f3", label: "Topic" },
                { color: "#ff5722", label: "Produces" },
                { color: "#9c27b0", label: "Consumes" }
            ];
            
            legendItems.forEach((item, i) => {
                const legendItem = legend.append("g")
                    .attr("transform", `translate(0, ${i * 20})`);
                    
                legendItem.append("rect")
                    .attr("width", 15)
                    .attr("height", 15)
                    .attr("fill", item.color);
                    
                legendItem.append("text")
                    .attr("x", 20)
                    .attr("y", 12)
                    .text(item.label);
            });
            
            // Update node and link positions on simulation tick
            sim.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                    
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                    
                label
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
            });
            
            // Drag functions
            function dragstarted(event, d) {
                if (!event.active) sim.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }
            
            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }
            
            function dragended(event, d) {
                if (!event.active) sim.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
            
            // Clear simulation on unmount
            return () => {
                sim.stop();
            };
        }, [data, selectedNode, selectedSchema, setSelectedNode]);
        
        return (
            <div className="graph-container">
                <svg ref={svgRef} style={{ width: '100%', height: '100%' }}></svg>
                <div className="controls">
                    <button onClick={() => {
                        const svg = d3.select(svgRef.current);
                        svg.call(d3.zoom().transform, d3.zoomIdentity);
                    }}>Reset View</button>
                    <button onClick={() => {
                        if (simulation) {
                            simulation.alpha(1).restart();
                        }
                    }}>Rearrange</button>
                </div>
            </div>
        );
    };

    // NodeDetails component
    const NodeDetails = ({ node, data }) => {
        if (!node) return null;
        
        if (node.type === 'service') {
            const producedTopics = data.links
                .filter(link => link.source === node.id && link.type === 'produces')
                .map(link => data.nodes.find(n => n.id === link.target));
                
            const consumedTopics = data.links
                .filter(link => link.target === node.id && link.type === 'consumes')
                .map(link => data.nodes.find(n => n.id === link.source));
                
            const usedSchemas = data.schemas.filter(schema => schema.services.includes(node.name));
            
            return (
                <div>
                    <h3>{node.name}</h3>
                    <p><strong>Type:</strong> Service</p>
                    <p><strong>Language:</strong> {node.language}</p>
                    
                    <h4>Produced Topics ({producedTopics.length})</h4>
                    <ul>
                        {producedTopics.map((topic, index) => (
                            <li key={index}>{topic.name}</li>
                        ))}
                    </ul>
                    
                    <h4>Consumed Topics ({consumedTopics.length})</h4>
                    <ul>
                        {consumedTopics.map((topic, index) => (
                            <li key={index}>{topic.name}</li>
                        ))}
                    </ul>
                    
                    <h4>Used Schemas ({usedSchemas.length})</h4>
                    <ul>
                        {usedSchemas.map((schema, index) => (
                            <li key={index}>
                                <div><strong>{schema.name}</strong></div>
                                <div><em>{schema.type}</em></div>
                                <div><small>{schema.namespace}</small></div>
                            </li>
                        ))}
                    </ul>
                </div>
            );
        } else if (node.type === 'topic') {
            const producers = node.producers || [];
            const consumers = node.consumers || [];
            
            return (
                <div>
                    <h3>{node.name}</h3>
                    <p><strong>Type:</strong> Topic</p>
                    
                    <h4>Producers ({producers.length})</h4>
                    <ul>
                        {producers.map((producer, index) => (
                            <li key={index}>{producer}</li>
                        ))}
                    </ul>
                    
                    <h4>Consumers ({consumers.length})</h4>
                    <ul>
                        {consumers.map((consumer, index) => (
                            <li key={index}>{consumer}</li>
                        ))}
                    </ul>
                </div>
            );
        }
        
        return <div>Unknown node type</div>;
    };

    // Render the App component to the DOM
    ReactDOM.render(
        <App />,
        document.getElementById('root')
    );
}"""

            # Write fallback files if template loading failed
            if "index_html" in locals():
                write_file(Path(output_dir), "index.html", index_html)
            if "css" in locals():
                write_file(Path(output_dir), "styles.css", css)
            if "app_js" in locals():
                write_file(Path(output_dir), "app.js", app_js)

        print(f"React app generated in {output_dir}")

    def generate_html(self, data: dict) -> str:
        """Generate HTML for the visualization."""
        # This method is required by BaseGenerator, but we're going to create a full app instead
        # Return an empty string as we'll generate the files directly in generate_output
        return ""

    def generate_output(self, data: dict, file_path: Path) -> None:
        """Generate the visualization output."""
        try:
            # Parse the JSON file
            services = self.parse_kafka_data(data)

            # Extract Kafka communication data
            kafka_data = self.extract_kafka_communication(services)

            # Generate the visualization data
            visualization_data = self.generate_visualization_data(services, kafka_data)

            # Generate the React app
            self.generate_react_app(visualization_data, file_path)

            print("Kafka communication visualization generated successfully!")
            print(f"\nVisualization generated at {file_path}")

        except Exception as e:
            print(f"Error generating visualization: {e}")
            raise
