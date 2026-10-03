const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,file);
const demoPath=path.resolve(__dirname,'../services/demo.ts');
function fresh(storage){delete require.cache[demoPath];global.window={localStorage:storage};return require(demoPath);}
let saved=null;
const storage={getItem:()=>saved,setItem:(key,value)=>{saved=value;}};
(async()=>{
  let demo=fresh(storage),snapshot=demo.readSnapshot();
  assert.equal(snapshot.lessons.length,3);
  snapshot.lessons[0].title='Changed';
  assert.notEqual(demo.readSnapshot().lessons[0].title,'Changed','snapshots must not alias internal state');
  snapshot.user={name:'Test',email:'test@example.test',password:'never-save'};
  snapshot.password='never-save';demo.saveSnapshot(snapshot);
  assert(!saved.includes('never-save'),'credentials must not persist');
  demo=fresh(storage);assert.equal(demo.readSnapshot().lessons[0].title,'Changed');
  for(const raw of ('not-json|{"lessons":[]}|{"user":null,"lessons":[{}],"notes":[],"chats":{},"reviews":{},"results":{}}').split('|')){
    saved=raw;demo=fresh(storage);assert.equal(demo.readSnapshot().lessons.length,3);
  }
  demo=fresh({getItem(){throw Error('blocked')},setItem(){throw Error('full')}});
  snapshot=demo.readSnapshot();snapshot.notes.push({id:'note-1',title:'Test',content:'Saved in session',updatedAt:new Date().toISOString()});
  demo.saveSnapshot(snapshot);assert.equal(demo.readSnapshot().notes[0].content,'Saved in session');
  const lesson=snapshot.lessons[0],bundle=demo.getLearningBundle(lesson);
  bundle.summary.keyPoints.length=0;assert(demo.getLearningBundle(lesson).summary.keyPoints.length);
  const questions=demo.getLearningBundle(lesson).quiz.questions;
  await assert.rejects(demo.demoQuiz(lesson,{}));
  const answers=Object.fromEntries(questions.map(q=>[q.id,q.answer]));
  assert.equal((await demo.demoQuiz(lesson,answers)).scorePercentage,100);
  answers[questions[0].id]=questions[0].options.find(o=>o!==questions[0].answer);
  assert.equal((await demo.demoQuiz(lesson,answers)).correctAnswers,questions.length-1);
  const chat=await demo.demoChat(lesson,'Nội dung nào?','easy');assert(chat.content.includes('không phải AI thật'));assert.equal(chat.sources.length,1);
  const custom={...lesson,id:'new-lesson',documents:[{...lesson.documents[0],id:'uploaded-user-file'}]};
  assert.equal((await demo.demoChat(custom,'Câu hỏi?','standard')).sources.length,0);
  assert(demo.getLearningBundle(custom).summary.overview.includes('không được tạo từ tài liệu'));
  console.log('Demo service checks passed: storage, corrupt data, credentials, fixtures, quiz and source labels.');
})().catch(e=>{console.error(e);process.exitCode=1});
