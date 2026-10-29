/** Bounded, exact-text three-way merge. This module never writes or renders a note. */
export const MERGE_LIMITS = {characters: 200_000, lines: 10_000, cells: 2_000_000} as const;

export type MergeSegment = {kind: "text"; text: string} | {
  kind: "conflict"; id: string; base: string; local: string; server: string;
  /** One-based lines in the common version; insertions use their insertion point. */
  startLine: number; endLine: number;
};
export type ReadyMergePlan = {
  kind: "ready"; segments: MergeSegment[]; conflictCount: number; comparedCells: number;
};
export type MergePlan = ReadyMergePlan | {kind: "unavailable"; reason: string};
type Hunk = {start: number; end: number; replacement: string[]};
type SideHunk = Hunk & {side: "local" | "server"};
type Budget = {cells: number};

// Keep each original line ending, including lone CR and a missing final newline.
const lines = (text: string): string[] => text.match(/[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$/g) || [];

function diff(base: string[], target: string[], budget: Budget): Hunk[] | null {
  let prefix = 0;
  while (prefix < base.length && prefix < target.length && base[prefix] === target[prefix]) prefix++;
  let baseEnd = base.length, targetEnd = target.length;
  while (baseEnd > prefix && targetEnd > prefix && base[baseEnd - 1] === target[targetEnd - 1]) {
    baseEnd--; targetEnd--;
  }
  const rows = baseEnd - prefix, columns = targetEnd - prefix;
  if (!rows && !columns) return [];
  if (!rows || !columns) return [{start: prefix, end: baseEnd, replacement: target.slice(prefix, targetEnd)}];
  const width = columns + 1, cells = (rows + 1) * width;
  if (budget.cells + cells > MERGE_LIMITS.cells) return null;
  budget.cells += cells;
  const lcs = new Uint32Array(cells);
  for (let i = rows - 1; i >= 0; i--) {
    for (let j = columns - 1; j >= 0; j--) {
      lcs[i * width + j] = base[prefix + i] === target[prefix + j]
        ? 1 + lcs[(i + 1) * width + j + 1]
        : Math.max(lcs[(i + 1) * width + j], lcs[i * width + j + 1]);
    }
  }
  const result: Hunk[] = [];
  let i = 0, j = 0, current: Hunk | undefined;
  const finish = () => {if (current) result.push(current); current = undefined;};
  while (i < rows || j < columns) {
    if (i < rows && j < columns && base[prefix + i] === target[prefix + j]) {
      finish(); i++; j++;
    } else {
      current ??= {start: prefix + i, end: prefix + i, replacement: []};
      if (j < columns && (i === rows || lcs[i * width + j + 1] > lcs[(i + 1) * width + j])) {
        current.replacement.push(target[prefix + j]); j++;
      } else {i++; current.end = prefix + i;}
    }
  }
  finish();
  return result;
}

function applyRange(base: string[], start: number, end: number, changes: SideHunk[]): string {
  let cursor = start;
  const text: string[] = [];
  for (const change of changes) {
    text.push(...base.slice(cursor, change.start), ...change.replacement);
    cursor = change.end;
  }
  text.push(...base.slice(cursor, end));
  return text.join("");
}

export function mergeText(base: string | null, local: string, server: string): MergePlan {
  if (base === null) return {kind: "unavailable", reason: "缺少可信的共同版本，请下载完整草稿和服务端版本，手动核对。"};
  if ([base, local, server].some(value => value.length > MERGE_LIMITS.characters)) {
    return {kind: "unavailable", reason: "任一版本超过 200,000 个字符，已停止自动比较；全文仍保留，可下载后手动核对。"};
  }
  const [baseLines, localLines, serverLines] = [base, local, server].map(lines);
  if ([baseLines, localLines, serverLines].some(value => value.length > MERGE_LIMITS.lines)) {
    return {kind: "unavailable", reason: "任一版本超过 10,000 行，已停止自动比较；全文仍保留，可下载后手动核对。"};
  }
  // Fast paths are allowed only after all input limits have been checked.
  if (local === server || local === base || server === base) {
    return {kind: "ready", segments: [{kind: "text", text: local === base ? server : local}], conflictCount: 0, comparedCells: 0};
  }
  const budget: Budget = {cells: 0};
  const localChanges = diff(baseLines, localLines, budget);
  const serverChanges = localChanges === null ? null : diff(baseLines, serverLines, budget);
  if (localChanges === null || serverChanges === null) {
    return {kind: "unavailable", reason: "差异比较超过 2,000,000 个计算单元，已停止自动合并；全文仍保留，可下载后手动核对。"};
  }
  const changes: SideHunk[] = [
    ...localChanges.map(change => ({...change, side: "local" as const})),
    ...serverChanges.map(change => ({...change, side: "server" as const})),
  ].sort((a, b) => a.start - b.start || a.end - b.end);
  const segments: MergeSegment[] = [];
  let pendingText: string[] = [];
  let cursor = 0, conflictCount = 0;
  const append = (text: string) => {
    if (text) pendingText.push(text);
  };
  const flushText = () => {
    if (pendingText.length) segments.push({kind: "text", text: pendingText.join("")});
    pendingText = [];
  };
  // Sorted interval groups are linear after sorting. Adjacent replacements are
  // independent; an insertion on either boundary is deliberately conservative.
  for (let index = 0; index < changes.length;) {
    const start = changes[index].start;
    let end = changes[index].end, insertionAtEnd = start === end;
    const group = [changes[index++]];
    while (index < changes.length) {
      const next = changes[index];
      const touches = next.start < end || (next.start === end && (insertionAtEnd || next.start === next.end));
      if (!touches) break;
      group.push(next); index++;
      if (next.end > end) {end = next.end; insertionAtEnd = next.start === next.end;}
      else if (next.start === end && next.end === end) insertionAtEnd = true;
    }
    append(baseLines.slice(cursor, start).join(""));
    const left = group.filter(change => change.side === "local");
    const right = group.filter(change => change.side === "server");
    const localText = applyRange(baseLines, start, end, left);
    const serverText = applyRange(baseLines, start, end, right);
    if (!left.length) append(serverText);
    else if (!right.length || localText === serverText) append(localText);
    else {
      flushText();
      conflictCount++;
      segments.push({kind: "conflict", id: `conflict-${conflictCount}`,
        base: baseLines.slice(start, end).join(""), local: localText, server: serverText,
        startLine: start + 1, endLine: Math.max(start + 1, end)});
    }
    cursor = end;
  }
  append(baseLines.slice(cursor).join(""));
  flushText();
  return {kind: "ready", segments, conflictCount, comparedCells: budget.cells};
}

export function resolveText(plan: ReadyMergePlan, choices: Record<string, "local" | "server">): string | null {
  const text: string[] = [];
  for (const segment of plan.segments) {
    if (segment.kind === "text") text.push(segment.text);
    else if (choices[segment.id] === "local") text.push(segment.local);
    else if (choices[segment.id] === "server") text.push(segment.server);
    else return null;
  }
  return text.join("");
}

function equalJson(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== "object" || typeof b !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const left = a as Record<string, unknown>, right = b as Record<string, unknown>;
  const keys = Object.keys(left);
  return keys.length === Object.keys(right).length && keys.every(key => Object.prototype.hasOwnProperty.call(right, key) && equalJson(left[key], right[key]));
}

/** Metadata is resolved as a whole field; conflicting arrays are never silently unioned. */
export function mergeField<T>(base: T, local: T, server: T): {conflict: boolean; value: T} {
  if (equalJson(local, server) || equalJson(server, base)) return {conflict: false, value: local};
  if (equalJson(local, base)) return {conflict: false, value: server};
  return {conflict: true, value: local};
}
