import test from 'node:test';
import assert from 'node:assert/strict';
import worker,{SAMPLE,parsePubmed,parseFDA,parseTrials,prepare,retrieve,collect} from './index.js';
const record=(id,text)=>({source:'pubmed',id,title:'Test',text,url:'https://pubmed.ncbi.nlm.nih.gov/'+id+'/'});
const call=(path,body,extra={})=>worker.fetch(new Request('https://example.test'+path,{method:'POST',headers:{'Content-Type':'application/json',...extra},body:JSON.stringify(body)}));
test('PubMed all sections, nested markup, negation and numeric entities',()=>{
 const rows=parsePubmed('<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><ArticleTitle>Drug <i>X</i></ArticleTitle><Abstract><AbstractText Label="METHODS">No <b>benefit</b>.</AbstractText><AbstractText Label="RESULTS">HER2-positive &#945; 20 mg.</AbstractText></Abstract></MedlineCitation></PubmedArticle></PubmedArticleSet>');
 assert.equal(rows.length,1);assert.equal(rows[0].title,'Drug X');assert.match(rows[0].text,/No benefit/);assert.match(rows[0].text,/α 20 mg/);assert.match(rows[0].text,/RESULTS:/);
});
test('FDA sections and trial v2 fields',()=>{
 assert.equal(parseFDA({results:[{id:'1',indications_and_usage:['one','two']} ]})[0].text,'one\ntwo');
 const r=parseTrials({studies:[{protocolSection:{identificationModule:{nctId:'NCT1'},descriptionModule:{briefSummary:'Text'},conditionsModule:{conditions:['Cancer']},armsInterventionsModule:{interventions:[{type:'DRUG',name:'X'}]}}}]})[0];
 assert.equal(r.metadata.interventions[0].name,'X');assert.equal(r.metadata.conditions[0],'Cancer');
});
test('quality flags duplicates, missing IDs and empty texts',()=>{
 const r=prepare([record('1','No benefit at 20 mg.'),record('1','Same'),record('2',''),record('','Text')]);
 assert.equal(r.documents.length,1);assert.deepEqual([r.quality.duplicates,r.quality.empty_text,r.quality.missing_id],[1,1,1]);assert.match(r.documents[0].text,/No benefit at 20 mg/);
});
test('TF-IDF ranks real sample drug and supports exact phrase and source filters',()=>{
 const hits=retrieve(SAMPLE.documents,'capecitabine breast cancer');assert.ok(hits.length);assert.match(hits[0].title.toLowerCase(),/capecitabine/);
 assert.ok(retrieve(SAMPLE.documents,'breast cancer',{source:'pubmed'}).every(r=>r.source==='pubmed'));
 assert.equal(retrieve(SAMPLE.documents,'breast cancer',{requiredTerm:'zzzz-no-such-term'}).length,0);
 assert.equal(retrieve([], 'cancer').length,0);assert.equal(retrieve([record('1','!!!')],'cancer').length,0);
});
test('chunk overlap covers the last words',()=>{
 const r=retrieve([record('1',Array.from({length:500},(_,i)=>'word'+i).join(' '))],'word499');assert.ok(r[0].passage.endsWith('word499'));
});
test('API validates JSON, source schemas, bounds and origin',async()=>{
 assert.equal((await call('/api/collect',{query:'cancer',limit:26})).status,400);
 assert.equal((await call('/api/search',{documents:[],question:''})).status,400);
 assert.equal((await call('/api/validate',{documents:[{id:'x'}]})).status,400);
 assert.equal((await call('/api/search',{documents:[],question:'test'},{Origin:'https://other.test'})).status,403);
 const r=await call('/api/search',{documents:SAMPLE.documents,question:'capecitabine breast cancer'});assert.equal(r.status,200);assert.ok((await r.json()).results.length);
});
test('home page embeds valid sample and executable client script',async()=>{
 const html=await(await worker.fetch(new Request('https://example.test/'))).text();assert.match(html,/Follow the evidence/);
 const data=html.match(/<script type="application\/json" id="sampleData">([\s\S]*?)<\/script>/)[1];assert.equal(JSON.parse(data).documents.length,9);
 const client=html.match(/<script>([\s\S]*?)<\/script>/)[1];new Function(client);
});
test('partial upstream failures are explicit and preserve successful results',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async input=>{const u=new URL(input);if(u.hostname.includes('ncbi'))return new Response(JSON.stringify({esearchresult:{idlist:[]}}));if(u.hostname==='api.fda.gov')return new Response('Bad request',{status:400});return new Response(JSON.stringify({studies:[{protocolSection:{identificationModule:{nctId:'NCT1'},descriptionModule:{briefSummary:'Trial evidence'}}}]}));};
 try{const r=await collect('test',5);assert.equal(r.status,'partial');assert.equal(r.source_status.fda.state,'failed');assert.equal(r.documents.length,1);assert.equal(r.raw_responses.length,3);}finally{globalThis.fetch=original;}
});
