const fs = require('fs'), vm = require('vm'), assert = require('assert'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../demo_live.html'), 'utf8');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {value:'', checked:false, disabled:false, hidden:false,
    textContent:'', style:{}, classList:{toggle(){},add(){},remove(){}}, replaceChildren(){},
    append(){},scrollIntoView(){},load(){},removeAttribute(){},files:[],querySelector:selector=>element(id+selector)});
  return elements.get(id);
}
let mode='success', requests=[], finish;
const context = {console, AbortController, setTimeout, clearTimeout, setInterval, clearInterval, Date,
  URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}}, window:{addEventListener(){}},
  document:{getElementById:element, querySelector:element,
    querySelectorAll:s=>s==='.source'?[element('source0'),element('source1')]:[], createElement:element},
  fetch:async (url, args)=>{
    if(url==='/api/status')return {ok:true,json:async()=>({simulated:false,model:'test',audio_available:true})};
    requests.push({url,args});
    if(mode==='wait')await new Promise(resolve=>finish=resolve);
    if(mode==='quota')return {ok:false,json:async()=>({code:'rate_limit',message:'Quota ngày',retryable:false,quota_kind:'daily'})};
    return {ok:true,json:async()=>({text:'SQLite truy vấn dữ liệu.',filename:'lecture.wav'})};
  }};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const run=s=>vm.runInContext(s,context);
(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(element('transcribe').disabled,true);
  const file={name:'lecture.wav',size:1200};element('audio-file').files=[file];run("$('audio-file').onchange()");
  assert.equal(element('transcribe').disabled,false);
  mode='wait';const pending=run("$('transcribe').onclick()");
  assert.equal(element('transcribe').disabled,true);
  assert.equal(element('audio-file').disabled,true);
  assert.equal(element('send').disabled,true);
  finish();await pending;
  assert.strictEqual(requests[0].args.body,file,'binary upload must use selected file');
  assert.equal(requests[0].args.headers['X-Audio-Filename'],'lecture.wav');
  assert.equal(element('transcript').value,'SQLite truy vấn dữ liệu.');
  assert.equal(element('transcript-only').checked,true);
  assert.equal(run('selectedSources()[0].text'),'SQLite truy vấn dữ liệu.');
  assert.equal(run('selectedSources()[0].segments.length'),0);
  element('audio-file').files=[{name:'other.wav',size:14000001}];run("$('audio-file').onchange()");
  assert.equal(element('transcribe').disabled,true);
  assert.equal(run('selectedSources().length'),0,'changing recording clears old transcript association');
  await run("$('transcribe').onclick()");assert.equal(requests.length,1);
  element('audio-file').files=[file];run("$('audio-file').onchange()");mode='quota';
  await run("$('transcribe').onclick()");
  assert.equal(element('transcribe').disabled,true);
  assert.equal(element('send').disabled,true);
  assert.equal(element('generate').disabled,true);
  assert.equal(element('transcript').value,'');
  await run("$('transcribe').onclick()");assert.equal(requests.length,2);
  console.log('Audio UI passed: upload, busy controls, automatic source, file switch, size rejection, shared quota.');
})().catch(e=>{console.error(e);process.exitCode=1});
