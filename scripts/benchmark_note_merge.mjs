// Run with Node 24: node scripts/benchmark_note_merge.mjs
// Synthetic text only; no files, browser storage, service or network is accessed.
import {performance} from 'node:perf_hooks';
import assert from 'node:assert/strict';
import {mergeText, resolveText} from '../frontend/src/features/notes/noteMerge.ts';

const iterations = 30;
const samples = [5000, 9999].map(count => {
  const lines = Array.from({length: count}, (_, i) => `笔记第${i + 1}行\n`);
  const local = [...lines], server = [...lines], expected = [...lines];
  local[20] = expected[20] = '本地补充 $x^2$\n';
  server[count - 20] = expected[count - 20] = '服务端补充\n';
  return {name: `${count}行稀疏修改`, base: lines.join(''), local: local.join(''), server: server.join(''), expected: expected.join('')};
});
samples.push({name: '9000行全面差异', base: '原文\n'.repeat(9000), local: '本地\n'.repeat(9000), server: '服务端\n'.repeat(9000), expected: null});
const results = [];
for (const sample of samples) {
  const run = () => mergeText(sample.base, sample.local, sample.server);
  for (let i = 0; i < 5; i++) run();
  const times = [];
  let result;
  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    result = run();
    times.push(performance.now() - start);
  }
  assert.equal(result.kind, sample.expected === null ? 'unavailable' : 'ready');
  if (result.kind === 'ready') assert.equal(resolveText(result, {}), sample.expected);
  times.sort((a, b) => a - b);
  results.push({sample: sample.name, medianMs: Number(((times[14] + times[15]) / 2).toFixed(3)), p95Ms: Number(times[28].toFixed(3)), result: result.kind, comparedCells: result.kind === 'ready' ? result.comparedCells : null});
}
console.log(JSON.stringify({node: process.version, warmups: 5, iterations, results}, null, 2));
