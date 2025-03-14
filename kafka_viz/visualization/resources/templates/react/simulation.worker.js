self.importScripts('https://d3js.org/d3.v7.min.js');

self.addEventListener('message', function (e) {
    const { nodes, links, width, height } = e.data;

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(50))
        .force("charge", d3.forceManyBody().strength(-100))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide().radius(30))
        .alphaDecay(0.05)
        .alphaMin(0.001);

    simulation.on("tick", () => {
        self.postMessage({ type: 'tick', nodes, links });
    });

    simulation.on("end", () => {
        self.postMessage({ type: 'end', nodes, links });
    });
});