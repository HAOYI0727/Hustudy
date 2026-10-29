import {useEffect, useId, useMemo, useRef, useState, type FormEvent} from 'react';
import {api, ApiError, type NoteGraphNode, type NoteGraphQuery, type NoteGraphResponse} from '../../api/client';
import {layoutNoteGraph, layoutNoteGraphLabels, NOTE_GRAPH_LAYOUT_LIMITS} from './noteGraphLayout';
import './note-graph.css';

type Props = {
  token: string; courseId: string; isOpen: boolean; initialFocusId?: string;
  hasDraft: boolean; disabled: boolean; onOpen: (node: NoteGraphNode) => void | Promise<void>;
  onError: (error: unknown) => void;
};
type LinkState = 'all' | 'linked' | 'isolated';

// The keyed child also discards old scope/input/selection when the account or course changes.
export default function NoteGraph(props: Props) {
  return props.isOpen ? <GraphWorkspace key={`${props.token}\0${props.courseId}\0${props.initialFocusId ?? ''}`} {...props}/> : null;
}

function GraphWorkspace({token, courseId, initialFocusId, hasDraft, disabled, onOpen, onError}: Props) {
  const [query, setQuery] = useState<NoteGraphQuery>(initialFocusId ? {focus_note_id: initialFocusId} : {});
  const [titleInput, setTitleInput] = useState(''), [linkInput, setLinkInput] = useState<LinkState>('all');
  const [refresh, setRefresh] = useState(0), [data, setData] = useState<NoteGraphResponse | null>(null);
  const [loading, setLoading] = useState(true), [error, setError] = useState(''), [unauthorized, setUnauthorized] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null), [zoom, setZoom] = useState(1);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const markerId = 'note-graph-arrow-' + useId().replace(/:/g, '');

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setData(null); setLoading(true); setError(''); setZoom(1);
    void api.noteGraph(token, courseId, query, controller.signal).then(result => {
      if (!active || controller.signal.aborted) return;
      if (result.course_id !== courseId || result.focus_note_id !== (query.focus_note_id ?? null)) throw new Error('返回的图谱范围已变化，请重试。');
      setData(result);
      setSelectedId(previous => result.nodes.some(node => node.id === previous) ? previous : result.focus_note_id);
    }).catch(failure => {
      if (!active || controller.signal.aborted) return;
      if (failure instanceof ApiError && failure.status === 401) {
        setUnauthorized(true);
        onErrorRef.current(failure);
        return;
      }
      setError(failure instanceof Error ? failure.message : '暂时无法读取笔记关系，请重试。');
    }).finally(() => {if (active && !controller.signal.aborted) setLoading(false);});
    return () => {active = false; controller.abort();};
  }, [token, courseId, query, refresh]);

  const layout = useMemo(() => layoutNoteGraph(data?.nodes ?? [], data?.edges ?? [], data?.focus_note_id), [data]);
  const nodeById = useMemo(() => new Map(data?.nodes.map(node => [node.id, node]) ?? []), [data]);
  const labels = useMemo(() => new Map(layoutNoteGraphLabels(layout, data?.nodes ?? [], selectedId).map(label => [label.id, label])), [layout, data, selectedId]);
  const selected = selectedId ? nodeById.get(selectedId) : undefined;
  const related = useMemo(() => {
    const result = new Set<string>();
    for (const edge of layout.edges) {
      if (edge.source_id === selectedId) result.add(edge.target_id);
      if (edge.target_id === selectedId) result.add(edge.source_id);
    }
    return result;
  }, [layout, selectedId]);
  const selectedPoint = layout.nodes.find(node => node.id === selectedId);
  const viewportWidth = layout.width / zoom, viewportHeight = layout.height / zoom;
  const centerX = selectedPoint?.x ?? layout.width / 2, centerY = selectedPoint?.y ?? layout.height / 2;
  const viewportX = Math.max(0, Math.min(layout.width - viewportWidth, centerX - viewportWidth / 2));
  const viewportY = Math.max(0, Math.min(layout.height - viewportHeight, centerY - viewportHeight / 2));
  const blocked = disabled || unauthorized;
  const pendingFilter = titleInput !== (query.q ?? '') || linkInput !== (query.link_state ?? 'all');
  const queryGraph = (event: FormEvent) => {event.preventDefault(); if (!blocked) setQuery({q: titleInput, link_state: linkInput});};
  const focus = () => {if (!selected || blocked) return; setTitleInput(''); setLinkInput('all'); setQuery({focus_note_id: selected.id});};
  const all = () => {setTitleInput(''); setLinkInput('all'); setQuery({});};

  return <section className="note-graph-workspace" aria-label="笔记关系图谱工作区" aria-busy={loading}>
    <div className="note-graph-intro">
      <p><strong>已保存关系</strong> · 箭头由插入双链的笔记指向被引用笔记。选择一个节点，查看它在课程中的连接。</p>
      <p className="hint">{hasDraft ? '当前有未保存草稿，图谱未包含这些更改；保存后可刷新图谱。' : '图谱按当前课程的已保存双链生成。'} 不包含回收站和其他课程的笔记。</p>
    </div>
    <form className="note-graph-search" onSubmit={queryGraph}>
      <label>按标题查找笔记<input value={titleInput} maxLength={200} onChange={event => setTitleInput(event.target.value)} disabled={blocked} placeholder="输入标题关键词"/></label>
      <label>关系筛选<select value={linkInput} onChange={event => setLinkInput(event.target.value as LinkState)} disabled={blocked}>
        <option value="all">全部笔记</option><option value="linked">已关联笔记</option><option value="isolated">孤立笔记</option>
      </select></label>
      <button type="submit" disabled={blocked}>查询</button>
      <button type="button" className="secondary" onClick={() => setRefresh(value => value + 1)} disabled={blocked || loading}>刷新图谱</button>
    </form>
    {pendingFilter && <p className="hint note-graph-pending">筛选已修改，点击“查询”应用。</p>}
    {(query.focus_note_id || query.q || query.link_state && query.link_state !== 'all') && <div className="note-graph-scope">
      <span>{query.focus_note_id ? '聚焦范围：中心笔记及其直接关联笔记' : `筛选范围：${query.q ? `标题包含“${query.q}”` : '任意标题'} · ${query.link_state === 'isolated' ? '孤立笔记' : query.link_state === 'linked' ? '已关联笔记' : '全部关系'}`}</span>
      <button type="button" className="secondary" disabled={blocked} onClick={all}>查看全课程</button>
    </div>}
    {loading && <p role="status" className="note-graph-state">正在读取已保存关系…</p>}
    {unauthorized && <p role="alert">登录已过期，请重新登录后打开图谱。</p>}
    {error && <div role="alert" className="note-graph-error"><p>{error}</p><button type="button" className="secondary" disabled={blocked} onClick={() => setRefresh(value => value + 1)}>重试图谱</button></div>}
    {data && <>
      <div className="note-graph-summary" role="status">显示 {data.nodes.length} / {data.total_nodes} 篇笔记 · {data.edges.length} / {data.total_edges} 条关系</div>
      {(data.nodes_truncated || data.edges_truncated) && <p className="note-graph-limit">当前范围超出显示上限（{data.node_limit} 篇笔记、{data.edge_limit} 条关系），仅显示其中一部分。请按标题缩小范围或聚焦一篇笔记；没有显示连线不代表没有关联。</p>}
      {!data.nodes.length ? <p className="note-graph-state">当前范围没有笔记。{query.focus_note_id || query.q || query.link_state && query.link_state !== 'all' ? '可查看全课程或修改筛选。' : '保存笔记并插入双链后，可在这里浏览关系。'}</p> : <div className="note-graph-layout">
        <div className="note-graph-visual">
          <div className="note-graph-zoom" aria-label="图谱视图控制">
            <span>关系方向 <span aria-hidden="true">→</span></span>
            <button type="button" className="secondary" aria-label="缩小图谱" disabled={zoom <= 1} onClick={() => setZoom(value => Math.max(1, value - .5))}>−</button>
            <span className="note-graph-scale">{Math.round(zoom * 100)}%</span>
            <button type="button" className="secondary" aria-label="放大图谱" disabled={zoom >= 3} onClick={() => setZoom(value => Math.min(3, value + .5))}>＋</button>
            <button type="button" className="secondary" onClick={() => setZoom(1)}>适合画布</button>
          </div>
          <svg className="note-graph-canvas" role="group" aria-label="有向笔记关系图" viewBox={`${viewportX} ${viewportY} ${viewportWidth} ${viewportHeight}`}>
            <defs>
              <marker id={markerId} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 z" className="note-graph-arrow"/></marker>
              <marker id={markerId + '-active'} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 8 4 L 0 8 z" className="note-graph-arrow-active"/></marker>
            </defs>
            <g aria-hidden="true">{layout.edges.map(edge => {
              const active = edge.source_id === selectedId || edge.target_id === selectedId;
              return <path key={edge.source_id + ':' + edge.target_id} d={edge.path} className={'note-graph-edge' + (active ? ' is-active' : '')} markerEnd={`url(#${markerId}${active ? '-active' : ''})`}/>;
            })}</g>
            {layout.nodes.map(point => {
              const node = nodeById.get(point.id)!;
              const label = labels.get(point.id);
              const active = point.id === selectedId, neighbor = related.has(point.id), isolated = node.incoming_count + node.outgoing_count === 0;
              return <g key={point.id} role="button" tabIndex={0} aria-label={'选择图中笔记：' + node.title} aria-pressed={active}
                className={'note-graph-node' + (active ? ' is-selected' : neighbor ? ' is-neighbor' : '') + (isolated ? ' is-isolated' : '')}
                transform={`translate(${point.x} ${point.y})`} onClick={() => setSelectedId(point.id)}
                onFocus={() => setZoom(1)} onKeyDown={event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); setSelectedId(point.id);}}}>
                <title>{node.title} · 入链 {node.incoming_count} · 出链 {node.outgoing_count}</title>
                <circle className="note-graph-node-halo" r={NOTE_GRAPH_LAYOUT_LIMITS.radius + 7}/>
                <circle className="note-graph-node-dot" r={NOTE_GRAPH_LAYOUT_LIMITS.radius}/>
                {label && <text x={label.x - point.x} y={label.y - point.y} textAnchor={label.anchor}>{label.text}</text>}
              </g>;
            })}
          </svg>
          <p className="hint note-graph-legend"><span className="note-graph-legend-dot"/>已有关联 <span className="note-graph-legend-dot is-isolated"/>课程内孤立 · 完整标题见笔记列表。放大时以选中节点为中心。</p>
        </div>
        <div className="note-graph-side">
          <section className="note-graph-inspector" aria-label="选中笔记">
            <h3>选中笔记</h3>
            {selected ? <>
              <strong className="note-graph-selected-title">{selected.title}</strong>
              <dl><dt>课程内入链</dt><dd>{selected.incoming_count}</dd><dt>课程内出链</dt><dd>{selected.outgoing_count}</dd></dl>
              <p className="hint">数量按完整课程计算，不受当前筛选或显示上限影响。</p>
              {selected.incoming_count + selected.outgoing_count === 0 && <p className="note-graph-isolated-label">这是一篇课程内孤立笔记。</p>}
              <p className="note-graph-tags">{selected.tags.length ? selected.tags.map(tag => <span key={tag}>#{tag}</span>) : <span className="hint">暂无标签</span>}</p>
              <p className="hint">更新于 {new Date(selected.updated_at).toLocaleString('zh-CN')}</p>
              <div className="note-graph-actions"><button type="button" disabled={blocked} onClick={() => void onOpen(selected)}>打开笔记</button><button type="button" className="secondary" disabled={blocked || loading} onClick={focus}>聚焦关联</button></div>
            </> : <p className="hint">选择图中节点或列表中的笔记，查看连接数量，再决定是否打开。</p>}
          </section>
          <div className="note-graph-directory"><h3>笔记列表 <small>{data.nodes.length}</small></h3>
            <ul aria-label="图谱笔记列表">{data.nodes.map(node => <li key={node.id}><button type="button" className="secondary" aria-label={'选择笔记：' + node.title} aria-pressed={selectedId === node.id} onClick={() => setSelectedId(node.id)}>
              <span>{node.title}</span><small>入链 {node.incoming_count} · 出链 {node.outgoing_count}{node.incoming_count + node.outgoing_count === 0 ? ' · 孤立' : ''}</small>
            </button></li>)}</ul>
          </div>
        </div>
      </div>}
    </>}
  </section>;
}
