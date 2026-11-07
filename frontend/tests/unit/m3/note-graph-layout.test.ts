import {describe, expect, it} from 'vitest';
import {graphTitle, layoutNoteGraph, layoutNoteGraphLabels, NOTE_GRAPH_LAYOUT_LIMITS} from '../../../src/features/notes/noteGraphLayout';

const node = (id: string, incoming = 0, outgoing = 0) => ({id, incoming_count: incoming, outgoing_count: outgoing});
const edge = (source_id: string, target_id: string) => ({source_id, target_id});

describe('笔记关系图谱有界布局', () => {
  it('空图和单点有有效画布，单点位于中心', () => {
    expect(layoutNoteGraph([], []).nodes).toEqual([]);
    const result = layoutNoteGraph([node('a')], []);
    expect(result.nodes).toEqual([{id: 'a', x: result.width / 2, y: result.height / 2}]);
    expect(result.width).toBeGreaterThan(0);
    expect(result.edges).toEqual([]);
  });

  it('同一节点和关系集合不因输入顺序不同而改变布局', () => {
    const nodes = [node('c', 0, 1), node('a', 1, 1), node('b', 2, 0)];
    const edges = [edge('c', 'a'), edge('a', 'b'), edge('b', 'a')];
    expect(layoutNoteGraph(nodes, edges)).toEqual(layoutNoteGraph([...nodes].reverse(), [...edges].reverse()));
  });

  it('聚焦笔记置于中心，即使它没有关系；不改变输入对象', () => {
    const nodes = Object.freeze([Object.freeze(node('busy', 20, 15)), Object.freeze(node('focus'))]);
    const edges = Object.freeze([Object.freeze(edge('busy', 'focus'))]);
    const result = layoutNoteGraph(nodes, edges, 'focus');
    expect(result.nodes[0]).toEqual({id: 'focus', x: result.width / 2, y: result.height / 2});
    expect(nodes[0].id).toBe('busy');
    expect(edges).toEqual([edge('busy', 'focus')]);
  });

  it('200 个节点都在画布内，圆点之间没有重叠', () => {
    const result = layoutNoteGraph(Array.from({length: 200}, (_, index) => node(String(index))), []);
    expect(result.nodes).toHaveLength(200);
    const invalidNodes: string[] = [];
    let minimumDistance = Infinity, checkedPairs = 0;
    for (let index = 0; index < result.nodes.length; index++) {
      const point = result.nodes[index], radius = NOTE_GRAPH_LAYOUT_LIMITS.radius;
      if (!Number.isFinite(point.x) || !Number.isFinite(point.y) ||
          point.x <= radius || point.y <= radius ||
          point.x >= result.width - radius || point.y >= result.height - radius) invalidNodes.push(point.id);
      for (let otherIndex = index + 1; otherIndex < result.nodes.length; otherIndex++) {
        const other = result.nodes[otherIndex];
        minimumDistance = Math.min(minimumDistance, Math.hypot(point.x - other.x, point.y - other.y));
        checkedPairs++;
      }
    }
    expect(invalidNodes).toEqual([]);
    expect(checkedPairs).toBe(200 * 199 / 2);
    expect(minimumDistance).toBeGreaterThan(40);
  });

  it('关系按方向去重并排除自环和未显示节点，双向箭头走不同曲线', () => {
    const result = layoutNoteGraph([node('a'), node('b')], [edge('a', 'a'), edge('a', 'b'), edge('a', 'b'), edge('b', 'a'), edge('b', 'missing')]);
    expect(result.edges).toHaveLength(2);
    expect(result.edges.map(({source_id, target_id}) => ({source_id, target_id}))).toEqual([edge('a', 'b'), edge('b', 'a')]);
    const paths = result.edges.map(item => item.path);
    expect(paths[0]).not.toBe(paths[1]);
    // Both directions have a control point displaced from the shared straight line.
    const x = result.nodes[0].x;
    const controls = paths.map(path => Number(path.split(' Q ')[1].split(' ')[0]));
    expect(controls[0]).not.toBe(x);
    expect(controls[0] - x).toBe(-(controls[1] - x));
  });

  it('异常超量输入仍限制 200 节点和 400 边并稳定截取', () => {
    const nodes = Array.from({length: 220}, (_, index) => node(String(index).padStart(3, '0')));
    const edges = nodes.flatMap(source => nodes.filter(target => source.id !== target.id).map(target => edge(source.id, target.id)));
    const result = layoutNoteGraph(nodes, edges);
    expect(result.nodes).toHaveLength(200);
    expect(result.edges).toHaveLength(400);
    expect(result).toEqual(layoutNoteGraph([...nodes].reverse(), [...edges].reverse()));
    expect(result.edges.every(item => !item.path.includes('NaN') && !item.path.includes('Infinity'))).toBe(true);
  });

  it('重复节点不会占据额外位置，找不到聚焦对象时仍有确定布局', () => {
    expect(layoutNoteGraph([node('a'), node('a'), node('b')], [], 'missing')).toEqual(layoutNoteGraph([node('a'), node('b')], []));
  });

  it('标题缩略保留完整 Unicode 字符，短标题不变', () => {
    expect(graphTitle('学习笔记')).toBe('学习笔记');
    expect(graphTitle('😀😀😀😀😀', 4)).toBe('😀😀😀…');
    expect(graphTitle('1234567890123')).toBe('12345678901…');
  });

  it('中心与左右邻居的长标题不相撞，选中标题优先且保留普通标题', () => {
    const nodes = [node('a', 1, 1), node('b', 1, 2), node('c', 1, 1), node('d', 1), node('o')];
    const titles = nodes.map(item => ({...item, title: item.id === 'b' ? 'B 双向关联·公式、概念与例题的长标题用于核对窄屏换行和完整名称' : `${item.id} 学习笔记`}));
    const graph = layoutNoteGraph(nodes, [edge('a', 'b'), edge('b', 'a'), edge('b', 'c'), edge('c', 'd')]);
    const labels = layoutNoteGraphLabels(graph, titles, 'a');
    expect(labels).toHaveLength(5);
    expect(labels[0].id).toBe('a');
    const collisions: string[] = [];
    for (let index = 0; index < labels.length; index++) {
      const a = labels[index];
      for (const b of labels.slice(index + 1)) if (a.left < b.left + b.width && a.left + a.width > b.left && a.top < b.top + b.height && a.top + a.height > b.top) collisions.push(`${a.id}:${b.id}`);
    }
    expect(collisions).toEqual([]);
  });

  it('32 篇长标题自动错位或缩略，标签不越界或覆盖圆点', () => {
    const nodes = Array.from({length: 32}, (_, index) => ({...node(String(index)), title: `第${index}篇关联学习内容和重要概念长标题`}));
    const graph = layoutNoteGraph(nodes, []), labels = layoutNoteGraphLabels(graph, nodes, '16');
    const failures: string[] = [];
    for (let index = 0; index < labels.length; index++) {
      const label = labels[index];
      if (label.left < 0 || label.top < 0 || label.left + label.width > graph.width || label.top + label.height > graph.height) failures.push('bounds:' + label.id);
      for (const point of graph.nodes) {
        const nearX = Math.max(label.left, Math.min(label.left + label.width, point.x)), nearY = Math.max(label.top, Math.min(label.top + label.height, point.y));
        if (Math.hypot(nearX - point.x, nearY - point.y) <= NOTE_GRAPH_LAYOUT_LIMITS.radius) failures.push('node:' + label.id);
      }
      for (const other of labels.slice(index + 1)) if (label.left < other.left + other.width && label.left + label.width > other.left && label.top < other.top + other.height && label.top + label.height > other.top) failures.push('label:' + label.id);
    }
    expect(failures).toEqual([]);
    expect(labels.some(label => label.id === '16')).toBe(true);
    expect(labels.length).toBeGreaterThan(16);
  });

  it('密集的 200 节点图任意选中节点都仍能显示自己的标题', () => {
    const nodes = Array.from({length: 200}, (_, index) => ({...node(String(index)), title: '长标题用于检查选中笔记始终可以辨认'}));
    const graph = layoutNoteGraph(nodes, []), missing: string[] = [];
    for (const selected of nodes) {
      const labels = layoutNoteGraphLabels(graph, nodes, selected.id);
      if (labels.length !== 1 || labels[0].id !== selected.id) missing.push(selected.id);
    }
    expect(missing).toEqual([]);
    expect(layoutNoteGraphLabels(graph, nodes)).toEqual([]);
  });
});
