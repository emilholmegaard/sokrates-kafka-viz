// Access the visualization data from the global scope
const visualizationData = window.visualizationData;

// Main App component
const App = () => {
    const [selectedNode, setSelectedNode] = React.useState(null);
    const [selectedSchema, setSelectedSchema] = React.useState(null);
    const [searchTerm, setSearchTerm] = React.useState("");
    
    const filteredSchemas = visualizationData.schemas.filter(schema => 
        schema.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        schema.namespace.toLowerCase().includes(searchTerm.toLowerCase()) ||
        schema.services.some(service => service.toLowerCase().includes(searchTerm.toLowerCase()))
    );
    
    return (
        <div className="app-container">
            <Graph 
                data={visualizationData} 
                selectedNode={selectedNode}
                setSelectedNode={setSelectedNode}
                selectedSchema={selectedSchema}
                setSelectedSchema={setSelectedSchema}
            />
            <div className="sidebar">
                <h2>Kafka Communication Details</h2>
                {selectedNode ? (
                    <NodeDetails node={selectedNode} data={visualizationData} />
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
