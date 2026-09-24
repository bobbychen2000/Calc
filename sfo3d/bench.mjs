import http from 'http'; import fs from 'fs'; import path from 'path';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = process.env.ROOT || new URL('.', import.meta.url).pathname.replace(/\/$/, '');
const srv=http.createServer((req,res)=>{ if(req.method==='POST'){let n=0;req.on('data',d=>n+=d.length);req.on('end',()=>{res.end(String(n));});return;}
 const f=path.join(root,req.url.split('?')[0]); fs.readFile(f,(e,d)=>{if(e){res.statusCode=404;return res.end();} res.setHeader('Content-Type', f.endsWith('.html')?'text/html':f.endsWith('.js')?'text/javascript':'application/octet-stream'); res.end(d);});}).listen(8765);
const b=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const p=await b.newPage(); p.on('console',m=>console.log('PAGE',m.text()));
await p.goto('http://localhost:8765/bench.html');
for (const [W,H,ms,tr,oct] of [[1920,1080,1,1e6,6],[3840,2160,1,1e6,6],[3840,2160,4,1e6,6],[3840,2160,1,1e6,12]]) {
  console.log(W,H,ms, JSON.stringify(await p.evaluate(([W,H,ms,tr,oct])=>bench(W,H,ms,tr,oct),[W,H,ms,tr,oct])));
}
await b.close(); srv.close();
