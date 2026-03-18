import { useEffect, useRef, useState, memo, useMemo } from 'react';

// Debounce utility
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function ClusterGraph({ clusters, posts }) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 300 });

  // Limit clusters to top 15 by influence for demo performance
  const limitedClusters = useMemo(() => {
    if (!clusters || clusters.length === 0) return [];

    return clusters
      .sort((a, b) => (b.influence_score || 0) - (a.influence_score || 0))
      .slice(0, 15);
  }, [clusters]);

  // Limit posts for better performance
  const limitedPosts = useMemo(() => {
    if (!posts || posts.length === 0) return [];
    return posts.slice(0, 20);
  }, [posts]);

  // Handle resize with debounce
  useEffect(() => {
    const updateDimensions = debounce(() => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: Math.max(300, width),
          height: Math.max(200, height),
        });
      }
    }, 150);

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (!svgRef.current || !limitedClusters || limitedClusters.length === 0) return;

    // Dynamic import d3 modules
    Promise.all([
      import('d3-force'),
      import('d3'),
    ]).then(([d3Force, d3]) => {
      renderGraph(d3Force, d3, svgRef.current, limitedClusters, limitedPosts, dimensions);
    }).catch(() => {
      // Silently handle D3 loading errors for demo
    });
  }, [limitedClusters, limitedPosts, dimensions]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: 280,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {(!limitedClusters || limitedClusters.length === 0) ? (
        <div style={{
          height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'rgba(255,255,255,0.3)',
        }}>
          No cluster data available
        </div>
      ) : (
        <>
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            style={{
              display: 'block',
              maxWidth: '100%',
              maxHeight: '100%',
            }}
            viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
            preserveAspectRatio="xMidYMid meet"
          />
          {clusters && clusters.length > 15 && (
            <div style={{
              position: 'absolute',
              bottom: 8,
              right: 8,
              fontSize: 10,
              color: 'rgba(255,255,255,0.4)',
              background: 'rgba(0,0,0,0.5)',
              padding: '4px 8px',
              borderRadius: 4,
            }}>
              Showing top 15 of {clusters.length} clusters for demo performance
            </div>
          )}
        </>
      )}
    </div>
  );
}

function renderGraph(d3Force, d3, svgEl, clusters, posts, dimensions) {
  const svg = d3.select(svgEl);
  svg.selectAll('*').remove();

  const width = dimensions.width;
  const height = dimensions.height;
  const padding = 50; // Padding from edges

  // Build nodes from clusters with safe defaults
  const nodes = clusters.map((c, index) => ({
    id: c.cluster_id ?? index,
    label: c.topic_label || `Cluster ${index + 1}`,
    size: Math.max(12, Math.min(35, ((c.post_count || 1) * 2.5))),
    influence: c.influence_score || 0,
    postCount: c.post_count || 0,
    avgVirality: c.avg_virality || 0,
  }));

  // Build links - use deterministic connections based on influence similarity
  const links = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      // Connect based on influence similarity (deterministic)
      const influenceDiff = Math.abs(nodes[i].influence - nodes[j].influence);
      const maxInfluence = Math.max(nodes[i].influence, nodes[j].influence, 1);
      const similarity = 1 - (influenceDiff / maxInfluence);

      if (similarity > 0.3 || (i + j) % 3 === 0) {
        links.push({
          source: nodes[i].id,
          target: nodes[j].id,
          strength: similarity,
        });
      }
    }
  }

  // Create simulation with strong boundary forces
  const simulation = d3Force.forceSimulation(nodes)
    .force('link', d3Force.forceLink(links).id((d) => d.id).distance(60).strength(0.3))
    .force('charge', d3Force.forceManyBody().strength(-80))
    .force('center', d3Force.forceCenter(width / 2, height / 2))
    .force('collision', d3Force.forceCollide().radius((d) => d.size + 8).strength(0.9))
    // Add boundary forces to keep nodes inside
    .force('x', d3Force.forceX(width / 2).strength(0.05))
    .force('y', d3Force.forceY(height / 2).strength(0.05));

  // Color scale - consistent colors
  const colors = ['#00d4ff', '#7b61ff', '#ff3d8e', '#00ff88', '#ff9f43', '#ff6b6b', '#48dbfb', '#feca57'];

  // Add gradient definitions for glow effect
  const defs = svg.append('defs');
  colors.forEach((color, i) => {
    const gradient = defs.append('radialGradient')
      .attr('id', `glow-${i}`)
      .attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', color).attr('stop-opacity', 0.8);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', color).attr('stop-opacity', 0.2);
  });

  // Draw links
  const link = svg.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', 'rgba(255,255,255,0.08)')
    .attr('stroke-width', (d) => Math.max(1, (d.strength || 0.5) * 2));

  // Draw nodes
  const node = svg.append('g')
    .attr('class', 'nodes')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', (d) => d.size)
    .attr('fill', (_, i) => `url(#glow-${i % colors.length})`)
    .attr('stroke', (_, i) => colors[i % colors.length])
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .style('filter', 'drop-shadow(0 0 4px rgba(0,0,0,0.3))');

  // Draw labels
  const label = svg.append('g')
    .attr('class', 'labels')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text((d) => {
      const text = d.label || '';
      return text.length > 15 ? text.substring(0, 15) + '...' : text;
    })
    .attr('font-size', 10)
    .attr('font-family', 'Inter, sans-serif')
    .attr('fill', 'rgba(255,255,255,0.8)')
    .attr('text-anchor', 'middle')
    .attr('dy', (d) => d.size + 14)
    .style('pointer-events', 'none')
    .style('text-shadow', '0 1px 2px rgba(0,0,0,0.8)');

  // Tooltips
  node.append('title')
    .text((d) => [
      d.label || 'Unknown Cluster',
      `Posts: ${d.postCount}`,
      `Influence: ${(d.influence || 0).toFixed(1)}`,
      `Avg Virality: ${(d.avgVirality || 0).toFixed(1)}`,
    ].join('\n'));

  // Clamp function to keep nodes within bounds
  const clampX = (x, r) => Math.max(padding + r, Math.min(width - padding - r, x));
  const clampY = (y, r) => Math.max(padding + r, Math.min(height - padding - r, y));

  simulation.on('tick', () => {
    // Clamp positions on every tick
    nodes.forEach((d) => {
      d.x = clampX(d.x, d.size);
      d.y = clampY(d.y, d.size);
    });

    link
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    node
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y);

    label
      .attr('x', (d) => d.x)
      .attr('y', (d) => d.y);
  });

  // Drag behavior
  node.call(
    d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        // Clamp drag position
        d.fx = clampX(event.x, d.size);
        d.fy = clampY(event.y, d.size);
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      })
  );

  // Initial "heat up" and cool down for better layout
  simulation.alpha(1).restart();
}

export default memo(ClusterGraph);
