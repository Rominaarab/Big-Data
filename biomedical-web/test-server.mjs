import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {SAMPLE} from './index.js';
const child=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:'4318'},stdio:['ignore','pipe','pipe']});
try{
 await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Server did not start')),8000);child.stdout.on('data',()=>{clearTimeout(timer);resolve();});child.on('error',reject);child.on('exit',code=>{if(code)reject(new Error('Server exited '+code));});});
 const health=await fetch('http://127.0.0.1:4318/api/health');assert.equal(health.status,200);assert.equal((await health.json()).status,'ok');
 const home=await fetch('http://127.0.0.1:4318/');assert.match(await home.text(),/Follow the evidence/);
 const answer=await fetch('http://127.0.0.1:4318/api/search',{method:'POST',headers:{'Content-Type':'application/json','Origin':'http://127.0.0.1:4318'},body:JSON.stringify({documents:SAMPLE.documents,question:'capecitabine breast cancer'})});assert.equal(answer.status,200);assert.ok((await answer.json()).results.length);
 console.log('Standalone server: health, HTML, same-origin search passed.');
}finally{child.kill();}
