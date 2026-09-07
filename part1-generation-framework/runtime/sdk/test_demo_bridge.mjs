/** Real Node client -> Python HTTP/SSE -> validator -> confirmation -> restore.
 * Fixtures test integration only; they are never counted as model quality.
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { once } from 'node:events';

const [python, demo] = process.argv.slice(2);
if (!python || !demo) throw new Error('Pass the Python executable and product Demo checkout');
const runtime = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { Part1Client } = await import(pathToFileURL(join(resolve(demo), 'lib/runtime-client.ts')).href);
const temp = await mkdtemp(join(tmpdir(), 'part1-bridge-'));
const token = randomBytes(24).toString('hex');
const scene = { understanding: '柔和灯光方便休息', relevance: .8, intent: 'vague', name: '小憩', logic: 'AND', conditions: [], actions: [{ primary: '氛围灯亮度', secondary: '20%' }, { primary: '主驾座椅加热', secondary: '1挡' }], say: '', offer: { type: 'none', target: '' }, memory: [], unsupported: [], warnings: [], clarify: null };
const fixture = join(temp, 'fixture.json'); await writeFile(fixture, JSON.stringify(scene));
const child = spawn(python, [join(runtime, 'server.py'), '--port', '0', '--fixture', fixture, '--storage', join(temp, 'state'), '--template', resolve(runtime, '../studies/round2/prompts/p19_zh.md')], { env: { ...process.env, PART1_RUNTIME_TOKEN: token, PYTHONIOENCODING: 'utf-8' }, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
let stderr = ''; child.stderr.on('data', chunk => { stderr += chunk; });
let timeout;
try {
  const ready = await Promise.race([once(child.stdout, 'data').then(([chunk]) => JSON.parse(chunk.toString().trim())), new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error('Runtime startup timed out')), 10000); })]);
  clearTimeout(timeout);
  const client = new Part1Client('http://' + ready.listening, token);
  const context = { driving: false, profile: 'none', vehicle: { 氛围灯亮度: '50%' } }, events = [];
  await client.generate({ input: '停车歇一会儿', model: 'deepseek-v4-flash', context }, e => events.push(e), AbortSignal.timeout(5000));
  assert.deepEqual(events.map(e => e.type), ['understanding', 'result']);
  const result = events[1].result, ref = result.runtime;
  assert.ok(ref.valid && ref.executable); assert.equal((await client.json('/state')).vehicle['氛围灯亮度'], '50%');
  await client.json('/confirm', { proposal_id: ref.proposalId, operation: 'apply_once', registry_revision: ref.registryRevision });
  let state = await client.json('/state');
  assert.equal(state.vehicle['氛围灯亮度'], '20%'); assert.equal(state.vehicle['主驾座椅加热'], undefined);
  await client.json('/simulation/advance', { seconds: 3 });
  state = await client.json('/state'); assert.equal(state.vehicle['主驾座椅加热'], '1挡');
  await client.json('/confirm', { proposal_id: ref.proposalId, operation: 'save', registry_revision: ref.registryRevision });
  await client.json('/restore', { proposal_id: ref.proposalId });
  state = await client.json('/state'); assert.deepEqual(state.vehicle, { 氛围灯亮度: '50%' });
  const invalid = await client.json('/demo/prepare', { scene: { ...scene, conditions: [{ primary: '车内PM2.5', secondary: '37μg/m³', op: '>' }] } });
  assert.equal(invalid.valid, false); assert.equal(invalid.scene.conditions.length, 1);
  await assert.rejects(client.json('/confirm', { proposal_id: invalid.proposal_id, operation: 'apply_once', registry_revision: invalid.registry_revision }));
  const proposal = await client.json('/demo/prepare', { scene });
  await client.json('/registry/toggle', { id: 'fragrance.power', enabled: false, registry_revision: proposal.registry_revision });
  await assert.rejects(client.json('/confirm', { proposal_id: proposal.proposal_id, operation: 'apply_once', registry_revision: proposal.registry_revision }), /Registry changed/);
  console.log(JSON.stringify({ passed: true, integration: 'Product TypeScript client -> real Python HTTP/SSE -> external validator -> confirmation -> 3-second trial -> save -> restore -> invalid trigger block -> hot-update stale block', paidModelCalls: 0 }));
} finally {
  clearTimeout(timeout); child.kill(); await once(child, 'exit').catch(() => {});
  // Verified task-owned temporary directory, using one API end-to-end.
  if (!resolve(temp).startsWith(resolve(tmpdir()) + '\\') && !resolve(temp).startsWith(resolve(tmpdir()) + '/')) throw new Error('Unexpected temp path');
  await rm(temp, { recursive: true, force: true });
  if (stderr) process.stderr.write(stderr);
}
