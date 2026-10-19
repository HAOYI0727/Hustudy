import {readFile, writeFile, readdir, access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join, dirname, relative, resolve} from 'node:path';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const lock = JSON.parse(await readFile(join(root, 'package-lock.json'), 'utf8'));
const visited = new Set();
const sections = ['Hustudy Markdown math: unmodified upstream packages. All rendering and fonts are bundled locally.\n'];
async function collect(name, from = root) {
  let directory;
  for (let parent = from; parent.startsWith(root); parent = dirname(parent)) {
    const candidate = join(parent, 'node_modules', name);
    try {await access(join(candidate, 'package.json')); directory = candidate; break;} catch {}
    if (parent === root) break;
  }
  if (!directory) throw new Error(`Missing math dependency: ${name}`);
  if (visited.has(directory)) return;
  visited.add(directory);
  const pkg = JSON.parse(await readFile(join(directory, 'package.json'), 'utf8'));
  const locked = lock.packages[relative(root, directory).replaceAll('\\', '/')];
  if (!locked || locked.version !== pkg.version) throw new Error(`Math dependency differs from lock: ${name}`);
  sections.push(`\n=== ${name} ${pkg.version} (${pkg.license}) ===\n${pkg.homepage || ''}\n`);
  const files = (await readdir(directory, {withFileTypes: true})).filter(entry => entry.isFile() && /license|notice|copying/i.test(entry.name));
  if (files.length) for (const file of files) sections.push(await readFile(join(directory, file.name), 'utf8'));
  else if (name === 'remark-math') sections.push(await readFile(join(root, 'licenses', 'remark-math-MIT.txt'), 'utf8'));
  else throw new Error(`Missing complete license: ${name}`);
  for (const dependency of Object.keys(pkg.dependencies || {}).sort()) await collect(dependency, directory);
}
for (const name of ['katex', 'remark-math', 'remark-parse', 'unified']) await collect(name);
await writeFile(join(root, 'public', 'math-notices.txt'), sections.join('\n').replaceAll('\r\n', '\n'));
console.log(`Local math notices built (${visited.size} packages).`);
