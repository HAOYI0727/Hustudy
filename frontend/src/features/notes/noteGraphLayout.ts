/** A bounded, deterministic layout; graph structure never depends on note bodies. */
export const NOTE_GRAPH_LAYOUT_LIMITS = {nodes: 200, edges: 400, radius: 14} as const;
export type GraphLayoutNode = {id: string; incoming_count: number; outgoing_count: number};
export type GraphLayoutEdge = {source_id: string; target_id: string};
export type GraphPoint = {id: string; x: number; y: number};
export type GraphPath = GraphLayoutEdge & {path: string};
export type GraphLayout = {width: number; height: number; nodes: GraphPoint[]; edges: GraphPath[]};
export type GraphLabel = {id: string; text: string; x: number; y: number; anchor: 'start' | 'middle' | 'end'; left: number; top: number; width: number; height: number};

const compareId = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;

export function layoutNoteGraph(nodes: readonly GraphLayoutNode[], edges: readonly GraphLayoutEdge[], focusId?: string | null): GraphLayout {
  const unique = new Map<string, GraphLayoutNode>();
  for (const node of nodes) if (!unique.has(node.id)) unique.set(node.id, node);
  const ordered = [...unique.values()].sort((a, b) =>
    Number(b.id === focusId) - Number(a.id === focusId) ||
    (b.incoming_count + b.outgoing_count) - (a.incoming_count + a.outgoing_count) || compareId(a.id, b.id)
  ).slice(0, NOTE_GRAPH_LAYOUT_LIMITS.nodes);
  // Rings hold increasingly many nodes, keeping target spacing above 75 units.
  const points: GraphPoint[] = [];
  let index = 0, ring = 0;
  while (index < ordered.length) {
    const capacity = ring === 0 ? 1 : 8 + (ring - 1) * 6;
    const count = Math.min(capacity, ordered.length - index), radius = ring * 100;
    for (let position = 0; position < count; position++) {
      const angle = -Math.PI / 2 + position * Math.PI * 2 / count;
      points.push({id: ordered[index++].id, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius});
    }
    ring++;
  }
  const extent = Math.max(170, (ring - 1) * 100 + 100), width = extent * 2, height = width;
  for (const point of points) {point.x += extent; point.y += extent;}
  const byId = new Map(points.map(point => [point.id, point]));
  const pairs = new Map<string, GraphLayoutEdge>();
  for (const edge of edges) {
    if (edge.source_id === edge.target_id || !byId.has(edge.source_id) || !byId.has(edge.target_id)) continue;
    pairs.set(JSON.stringify([edge.source_id, edge.target_id]), edge);
  }
  const visibleEdges = [...pairs.values()].sort((a, b) => compareId(a.source_id, b.source_id) || compareId(a.target_id, b.target_id)).slice(0, NOTE_GRAPH_LAYOUT_LIMITS.edges);
  const paths = visibleEdges.map(edge => {
    const source = byId.get(edge.source_id)!, target = byId.get(edge.target_id)!;
    const dx = target.x - source.x, dy = target.y - source.y, distance = Math.hypot(dx, dy);
    const nx = dx / distance, ny = dy / distance, inset = NOTE_GRAPH_LAYOUT_LIMITS.radius + 5;
    const bend = pairs.has(JSON.stringify([edge.target_id, edge.source_id])) ? 24 : 0;
    const startX = source.x + nx * inset, startY = source.y + ny * inset;
    const endX = target.x - nx * inset, endY = target.y - ny * inset;
    const controlX = (source.x + target.x) / 2 - ny * bend, controlY = (source.y + target.y) / 2 + nx * bend;
    return {...edge, path: `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`};
  });
  return {width, height, nodes: points, edges: paths};
}

export function graphTitle(title: string, limit = 12): string {
  const letters = Array.from(title);
  return letters.length <= limit ? title : letters.slice(0, Math.max(1, limit - 1)).join('') + '…';
}

/** Reserve space for the selected label first; never overlap another label or node. */
export function layoutNoteGraphLabels(layout: GraphLayout, notes: readonly {id: string; title: string}[], selectedId?: string | null): GraphLabel[] {
  const titles = new Map(notes.map(note => [note.id, note.title]));
  const ordered = layout.nodes.filter(point => titles.has(point.id) && (layout.nodes.length <= 32 || point.id === selectedId))
    .sort((a, b) => Number(b.id === selectedId) - Number(a.id === selectedId));
  const labels: GraphLabel[] = [];
  for (const point of ordered) {
    const horizontal = point.x - layout.width / 2, vertical = point.y - layout.height / 2;
    const above = {x: point.x, y: point.y - 31, anchor: 'middle' as const};
    const below = {x: point.x, y: point.y + 43, anchor: 'middle' as const};
    const left = {x: point.x - 30, y: point.y + 6, anchor: 'end' as const};
    const right = {x: point.x + 30, y: point.y + 6, anchor: 'start' as const};
    const outward = Math.abs(horizontal) > Math.abs(vertical) + 1 ? horizontal < 0 ? left : right : vertical < 0 ? above : below;
    const candidates = [outward, below, above, right, left,
      {x: point.x + 24, y: point.y - 24, anchor: 'start' as const},
      {x: point.x - 24, y: point.y - 24, anchor: 'end' as const},
      {x: point.x + 24, y: point.y + 36, anchor: 'start' as const},
      {x: point.x - 24, y: point.y + 36, anchor: 'end' as const},
      {x: point.x, y: point.y + 62, anchor: 'middle' as const},
      {x: point.x, y: point.y - 50, anchor: 'middle' as const}];
    let found: GraphLabel | undefined;
    for (const budget of point.id === selectedId ? [12, 10, 8, 6, 4] : [10, 8, 6, 4]) {
      const text = graphTitle(titles.get(point.id)!, budget);
      // A conservative full-width character box includes bold text and its outline.
      const width = Array.from(text).length * 16 + 4, height = 24;
      for (const candidate of candidates) {
        const left = candidate.x - (candidate.anchor === 'middle' ? width / 2 : candidate.anchor === 'end' ? width : 0), top = candidate.y - 18;
        if (left < 6 || top < 6 || left + width > layout.width - 6 || top + height > layout.height - 6) continue;
        if (labels.some(label => left < label.left + label.width + 6 && left + width + 6 > label.left && top < label.top + label.height + 6 && top + height + 6 > label.top)) continue;
        if (layout.nodes.some(node => {
          const nearX = Math.max(left, Math.min(left + width, node.x)), nearY = Math.max(top, Math.min(top + height, node.y));
          return Math.hypot(nearX - node.x, nearY - node.y) < NOTE_GRAPH_LAYOUT_LIMITS.radius + 8;
        })) continue;
        found = {id: point.id, text, ...candidate, left, top, width, height};
        break;
      }
      if (found) break;
    }
    if (found) labels.push(found);
  }
  return labels;
}
