// Standalone Node host for the same Worker module (Docker-compatible).
import http from 'node:http';
import worker from './index.js';
const maxBytes=1500000;
const server=http.createServer(async(req,res)=>{
  try{
    if(Number(req.headers['content-length']||0)>maxBytes){res.writeHead(413,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Request too large.'}));req.resume();return;}
    const buffers=[];let size=0;
    for await(const chunk of req){size+=chunk.length;if(size>maxBytes){res.writeHead(413,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Request too large.'}));return;}buffers.push(chunk);}
    const origin='http://'+(req.headers.host||'localhost');
    const request=new Request(origin+req.url,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(buffers)}:{})});
    const response=await worker.fetch(request,process.env);
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));
  }catch{res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'The server could not complete the request.'}));}
});
const port=Number(process.env.PORT||8080);
server.listen(port,'0.0.0.0',()=>console.log('Evidence Explorer listening on port '+port));
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>server.close(()=>process.exit(0)));
