// Enhanced app.js with debugging
console.log('React initialization starting...');

try {
    // Check if dependencies are loaded
    console.log('Checking dependencies:', {
        react: typeof React !== 'undefined',
        reactDOM: typeof ReactDOM !== 'undefined',
        d3: typeof d3 !== 'undefined',
        babel: typeof Babel !== 'undefined'
    });

    // Check visualization data
    console.log('Checking visualization data...');
    if (!window.visualizationData) {
        console.error('ERROR: visualizationData is not defined!');
        document.getElementById('root').innerHTML = '<div style="color: red; padding: 20px;">Error: No visualization data found. Please regenerate the visualization.</div>';
        throw new Error('visualizationData not found');
    }

    console.log('Visualization data loaded:', {
        nodes: window.visualizationData.nodes?.length || 0,
        links: window.visualizationData.links?.length || 0,
        schemas: window.visualizationData.schemas?.length || 0
    });

    // Log a sample of visualization data for debugging
    if (window.visualizationData.nodes?.length > 0) {
        console.log('Sample node:', window.visualizationData.nodes[0]);
    }
    if (window.visualizationData.links?.length > 0) {
        console.log('Sample link:', window.visualizationData.links[0]);
    }
    if (window.visualizationData.schemas?.length > 0) {
        console.log('Sample schema:', window.visualizationData.schemas[0]);
    }

    // Main App component
    console.log('Defining React components...');
    const App = () => {
        console.log('App component rendering');
        const [selectedNode, setSelectedNode] = React.useState(null);
        const [selectedSchema, setSelectedSchema] = React.useState(null);
        const [searchTerm, setSearchTerm] = React.useState("");

        const filteredSchemas = React.useMemo(() =>
            window.visualizationData.schemas.filter(schema =>
                schema.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                schema.namespace.toLowerCase().includes(searchTerm.toLowerCase()) ||
                schema.services.some(service =>
                    service.toLowerCase().includes(searchTerm.toLowerCase()))
            ),
            [searchTerm]
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
        console.log('Graph component rendering');
        const svgRef = React.useRef(null);
        const [simulation, setSimulation] = React.useState(null);

        // Initialize and update the D3 force simulation
        React.useEffect(() => {
            console.log('Graph useEffect running');

            try {
                if (!data) {
                    console.error('No data provided to Graph component');
                    return;
                }

                if (!svgRef.current) {
                    console.error('SVG ref is not available');
                    return;
                }

                console.log('Initializing D3 visualization with:', {
                    nodes: data.nodes.length,
                    links: data.links.length
                });

                const width = svgRef.current.parentElement.clientWidth;
                const height = svgRef.current.parentElement.clientHeight;

                console.log('Graph dimensions:', { width, height });

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

                // Add this before creating the simulation:
                // Pre-position nodes in a grid layout
                const gridSize = Math.ceil(Math.sqrt(data.nodes.length));
                data.nodes.forEach((node, i) => {
                    node.x = (i % gridSize) * 100 + width / 4;
                    node.y = Math.floor(i / gridSize) * 100 + height / 4;
                });

                // Create a force simulation on main thread directly
                console.log('Creating force simulation on main thread');
                const sim = d3.forceSimulation(data.nodes)
                    .force("link", d3.forceLink(data.links).id(d => d.id).distance(50))
                    .force("charge", d3.forceManyBody().strength(-100))
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collide", d3.forceCollide().radius(30))
                    .alphaDecay(0.05)
                    .alphaMin(0.001);

                setSimulation(sim);

                // Draw links
                console.log('Drawing links');
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
                console.log('Drawing nodes');
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

                console.log('Visualization elements created successfully');

                // On each tick, update the visualization
                sim.on("tick", () => {
                    // Only update visible elements
                    const transform = d3.zoomTransform(svg.node());

                    link
                        .attr("visibility", d =>
                            isNodeInViewport(d.source, transform) &&
                                isNodeInViewport(d.target, transform) ? "visible" : "hidden")
                        .filter(d => isNodeInViewport(d.source, transform) &&
                            isNodeInViewport(d.target, transform))
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);

                    node
                        .attr("visibility", d =>
                            isNodeInViewport(d, transform) ? "visible" : "hidden")
                        .filter(d => isNodeInViewport(d, transform))
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);

                    label
                        .attr("visibility", d =>
                            isNodeInViewport(d, transform) ? "visible" : "hidden")
                        .filter(d => isNodeInViewport(d, transform))
                        .attr("x", d => d.x)
                        .attr("y", d => d.y);
                });

                // Notify when simulation is done
                sim.on("end", () => {
                    console.log('Simulation completed!');
                    // Here is where you'd update the loading progress to 100%
                    if (window.updateLoadingProgress && window.LoadingStates) {
                        window.updateLoadingProgress(window.LoadingStates.COMPLETE);
                    }
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

                // Add this function inside the Graph component:
                function isNodeInViewport(d, transform) {
                    const padding = 100; // pixels
                    const x = transform.applyX(d.x);
                    const y = transform.applyY(d.y);
                    return x >= -padding &&
                        x <= width + padding &&
                        y >= -padding &&
                        y <= height + padding;
                }

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

                console.log('D3 visualization setup complete');

                // Clear simulation on unmount
                return () => {
                    console.log('Cleaning up simulation');
                    sim.stop();
                };
            } catch (error) {
                console.error('Error in Graph useEffect:', error);
            }
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
    const NodeDetails = React.memo(({ node, data }) => {
        console.log('NodeDetails rendering for node:', node?.name);

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
    });

    // Render the App component to the DOM
    console.log('Rendering React app to DOM...');
    ReactDOM.render(
        <App />,
        document.getElementById('root')
    );
    console.log('React app rendered successfully!');

    // Manually set progress to complete after a short delay
    setTimeout(() => {
        if (window.updateLoadingProgress && window.LoadingStates) {
            window.updateLoadingProgress(window.LoadingStates.COMPLETE);
        }
    }, 2000);

} catch (error) {
    console.error('Fatal error in React application:', error);
    document.getElementById('root').innerHTML = `
    <div style="color: red; padding: 20px; background-color: #ffeeee; border: 1px solid #ffaaaa;">
      <h2>React Application Error</h2>
      <p><strong>Error message:</strong> ${error.message}</p>
      <p>Please check the browser console for more details.</p>
      <p><strong>Debugging steps:</strong></p>
      <ol>
        <li>Check that visualization-data.js is loaded correctly</li>
        <li>Verify that all React dependencies are loaded</li>
        <li>Inspect the browser's console for detailed error messages</li>
      </ol>
    </div>
  `;
}