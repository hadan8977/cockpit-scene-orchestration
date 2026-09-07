/** Start both reviewed services locally without persisting or printing tokens. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';

const [python, demoPath, privateEnv, candidate = 'p24_zh.md'] = process.argv.slice(2);
if (!python || !demoPath || !privateEnv) throw new Error('Usage: node start_demo.mjs <python> <SceneStudio repository> <private env file> [candidate file]');
const part = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const template = path.resolve(part, 'studies/round2/prompts', candidate);
if (!template.startsWith(path.join(part, 'studies/round2/prompts') + path.sep) || !fs.existsSync(template)) throw new Error('Unknown candidate template');
const demo = path.resolve(demoPath), envFile = path.resolve(privateEnv);
if (!fs.existsSync(path.join(demo,'.next/BUILD_ID')) || !fs.existsSync(envFile)) throw new Error('Build the product Demo and provide its private model environment file first');
const token = randomBytes(32).toString('base64url');
const pythonEnv = { ...process.env, PART1_RUNTIME_TOKEN: token };
const children = [];
function cleanup() {
  for (const child of children) {
    if (!child.pid) continue;
    if (process.platform === 'win32') spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
    else child.kill('SIGTERM');
  }
}
process.on('SIGINT',()=>{cleanup();process.exit(0);});
process.on('SIGTERM',()=>{cleanup();process.exit(0);});
const runtime = spawn(python,[path.join(part,'runtime/server.py'),'--port','8787','--env-file',envFile,'--mode','strict_tool','--template',template],{cwd:part,env:pythonEnv,windowsHide:true,stdio:['ignore','pipe','pipe']});
children.push(runtime);
runtime.stderr.on('data',chunk=>process.stderr.write(chunk));
await new Promise((resolve,reject)=>{runtime.stdout.once('data',()=>resolve());runtime.once('error',reject);runtime.once('exit',code=>reject(new Error('Runtime stopped: '+code)));});
const app = spawn(process.execPath,[path.join(demo,'node_modules/next/dist/bin/next'),'start','--port','3101','--hostname','127.0.0.1'],{cwd:demo,env:{...process.env,PART1_RUNTIME_TOKEN:token,PART1_RUNTIME_URL:'http://127.0.0.1:8787'},windowsHide:true,stdio:['ignore','pipe','pipe']});
children.push(app);
app.stdout.on('data',chunk=>process.stdout.write(chunk));app.stderr.on('data',chunk=>process.stderr.write(chunk));
app.once('exit',code=>{cleanup();process.exit(code||0);});
runtime.once('exit',()=>{cleanup();process.exit(1);});
console.log(JSON.stringify({product:'http://127.0.0.1:3101',mode:'strict_tool',simulation:true,candidate,qualityAcceptance:'See round2 report; launching does not imply acceptance',secretsPrinted:false}));
