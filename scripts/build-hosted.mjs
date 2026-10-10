import fs from 'node:fs';
import path from 'node:path';
const assets={};
function collect(dir,prefix=''){for(const name of fs.readdirSync(dir)){if(name==='server'||name==='.openai')continue;const full=path.join(dir,name),url=prefix+'/'+name;if(fs.statSync(full).isDirectory())collect(full,url);else assets[url]=fs.readFileSync(full).toString('base64');}}
collect('dist');
// Keep the local key-entry flow; hosted credentials are managed by Sites secrets.
let head=Buffer.from(assets['/security-head.js'],'base64').toString();
head=head.replace(/<form id="head-mistral-config">[\s\S]*?<\/form>/,'<p class="hint">Groq is connected through a server secret. Use Test AI live to verify the connection.</p>');
head=head.replace(/<p class="hint">Free Ollama API on this computer\.[\s\S]*?<\/p>/,'');
head=head.replace('Groq / Mistral online API + local backup','Groq online AI').replaceAll('Shared localhost records','Shared online records').replaceAll('through local SQLite','through the hosted database');
assets['/security-head.js']=Buffer.from(head).toString('base64');
assets['/shared-state.js']=Buffer.from(Buffer.from(assets['/shared-state.js'],'base64').toString().replaceAll('SQLite revision','Shared revision')).toString('base64');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.css':'text/css; charset=utf-8','.txt':'text/plain; charset=utf-8'};
let source=fs.readFileSync('worker/api.mjs','utf8');source+='\nconst assets='+JSON.stringify(assets)+';\nconst types='+JSON.stringify(types)+';\n';
source+=`export default {async fetch(request,env){const u=new URL(request.url);if(u.pathname.startsWith('/api/'))return api(request,env);if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405});const key=u.pathname==='/'?'/index.html':u.pathname;const asset=assets[key];if(!asset)return new Response('Not found',{status:404});const content=Uint8Array.from(atob(asset),c=>c.charCodeAt(0));return new Response(request.method==='HEAD'?null:content,{headers:{'Content-Type':types[key.slice(key.lastIndexOf('.'))]||'application/octet-stream','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'}});}};`;
fs.mkdirSync('dist/server',{recursive:true});fs.writeFileSync('dist/server/index.js',source);
fs.mkdirSync('dist/.openai',{recursive:true});fs.copyFileSync('.openai/hosting.json','dist/.openai/hosting.json');fs.cpSync('drizzle','dist/.openai/drizzle',{recursive:true});
console.log('Built hosted Worker with '+Object.keys(assets).length+' assets and D1 schema migration.');
