import type {ChatMessage, DemoSnapshot, Lesson, LearningBundle, QuizResult, TutorMode} from '../types';
import {genericFixture, initialSnapshot, learningFixtures} from './fixtures';

const STORAGE_KEY = 'ai-study-assistant.frontend-demo.v1';
let memory: DemoSnapshot | null = null;
const clone = <T>(value:T):T => JSON.parse(JSON.stringify(value));
const record = (x:unknown): x is Record<string,unknown> => !!x && typeof x === 'object' && !Array.isArray(x);
const text = (x:unknown): x is string => typeof x === 'string';
const finite = (x:unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const all = (x:unknown, check:(item:unknown)=>boolean):boolean => Array.isArray(x) && x.every(check);
const values = (x:unknown, check:(item:unknown)=>boolean):boolean => record(x) && Object.values(x).every(check);

function isSnapshot(x:unknown): x is DemoSnapshot {
  if (!record(x)) return false;
  const doc=(d:unknown)=>record(d)&&text(d.id)&&text(d.name)&&finite(d.size)&&text(d.mediaType)
    &&['ready','pending','processing','failed'].includes(String(d.status))&&['demo','live'].includes(String(d.sourceMode))
    &&(d.transcript===undefined||text(d.transcript));
  const lesson=(l:unknown)=>record(l)&&text(l.id)&&text(l.title)&&text(l.description)&&text(l.topic)
    &&['mint','lavender','peach','blue'].includes(String(l.accent))&&text(l.createdAt)&&finite(l.progress)&&all(l.documents,doc);
  const message=(m:unknown)=>record(m)&&text(m.id)&&['user','assistant'].includes(String(m.role))&&text(m.content)
    &&(m.sources===undefined||all(m.sources,s=>record(s)&&text(s.id)&&text(s.name)));
  const result=(r:unknown)=>record(r)&&text(r.id)&&text(r.completedAt)&&finite(r.scorePercentage)&&finite(r.correctAnswers)&&finite(r.totalQuestions)
    &&all(r.details,d=>record(d)&&text(d.questionId)&&text(d.selected)&&text(d.correct)&&typeof d.isCorrect==='boolean'&&text(d.explanation));
  return (x.user===null||(record(x.user)&&text(x.user.name)&&text(x.user.email)))
    &&all(x.lessons,lesson)&&all(x.notes,n=>record(n)&&text(n.id)&&text(n.title)&&text(n.content)&&text(n.updatedAt))
    &&values(x.chats,c=>all(c,message))&&values(x.reviews,r=>values(r,v=>['again','hard','good','easy'].includes(String(v))))
    &&values(x.results,r=>all(r,result));
}

export function uid(prefix:string):string {
  return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
}
export function readSnapshot():DemoSnapshot {
  if (memory) return clone(memory);
  try {
    const raw=typeof window!=='undefined'?window.localStorage.getItem(STORAGE_KEY):null;
    if (raw) {const parsed:unknown=JSON.parse(raw);if(isSnapshot(parsed)) {memory=parsed;return clone(parsed);}}
  } catch { /* Blocked storage or corrupt data: start an offline session. */ }
  memory=initialSnapshot();return clone(memory);
}
export function saveSnapshot(snapshot:DemoSnapshot):void {
  if(!isSnapshot(snapshot))throw new Error('Trạng thái demo không hợp lệ.');
  // Select known fields, so arbitrary credentials cannot enter storage.
  memory=clone({lessons:snapshot.lessons,notes:snapshot.notes,chats:snapshot.chats,
    reviews:snapshot.reviews,results:snapshot.results,
    user:snapshot.user?{name:snapshot.user.name,email:snapshot.user.email}:null});
  try {if(typeof window!=='undefined')window.localStorage.setItem(STORAGE_KEY,JSON.stringify(memory));}
  catch { /* Session memory remains available if storage is full/blocked. */ }
}
export function getLearningBundle(lesson:Lesson):LearningBundle {
  return clone(Object.hasOwn(learningFixtures,lesson.id)?learningFixtures[lesson.id]:genericFixture);
}
const GEMINI_KEY_STORAGE='ai-study-assistant.gemini-key';
const GEMINI_MODELS=['gemini-3.8-flash','gemini-3.7-flash','gemini-3.5-flash-lite'];

function getGeminiKey():string {
  if(typeof window==='undefined')throw new Error('Gemini chỉ hoạt động trên trình duyệt.');
  let apiKey=window.sessionStorage.getItem(GEMINI_KEY_STORAGE)?.trim()||'';
  if(!apiKey){
    apiKey=window.prompt('Nhập Gemini API key để bật xử lý tài liệu và AI Tutor. Key chỉ được giữ trong tab trình duyệt này.')?.trim()||'';
    if(!apiKey)throw new Error('Chưa có Gemini API key.');
    window.sessionStorage.setItem(GEMINI_KEY_STORAGE,apiKey);
  }
  return apiKey;
}

async function callGemini(apiKey:string, body:unknown):Promise<any> {
  let data:any=null;
  let lastError='Gemini chưa phản hồi.';
  for(const model of GEMINI_MODELS){
    for(let attempt=0;attempt<2;attempt++){
      const response=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,{
        method:'POST',
        headers:{'Content-Type':'application/json','x-goog-api-key':apiKey},
        body:JSON.stringify(body)
      });
      data=await response.json().catch(()=>null);
      if(response.ok)return data;
      const message=data?.error?.message||`Gemini trả lỗi HTTP ${response.status}.`;
      lastError=message;
      if(response.status===400||response.status===401||response.status===403){
        window.sessionStorage.removeItem(GEMINI_KEY_STORAGE);
        throw new Error('Gemini API key không hợp lệ hoặc không có quyền sử dụng API.');
      }
      const retryable=response.status===429||response.status===503||/high demand|overloaded|temporar|try again/i.test(message);
      if(!retryable)break;
      if(attempt===0)await new Promise(resolve=>setTimeout(resolve,700));
    }
  }
  throw new Error(lastError);
}

function geminiText(data:any):string {
  return (data?.candidates?.[0]?.content?.parts||[])
    .map((part:{text?:string})=>part.text||'').join('').trim();
}

async function fileToBase64(file:File):Promise<string> {
  const bytes=new Uint8Array(await file.arrayBuffer());
  let binary='';
  const chunk=0x8000;
  for(let i=0;i<bytes.length;i+=chunk)binary+=String.fromCharCode(...bytes.subarray(i,i+chunk));
  return btoa(binary);
}

export async function processStudyFile(file:File):Promise<string> {
  if(file.size>20*1024*1024)throw new Error(`${file.name}: file quá lớn để xử lý trực tiếp trên GitHub Pages (tối đa 20 MB).`);
  const lower=file.name.toLowerCase();
  if(/\.(txt|md)$/i.test(lower)){
    const content=(await file.text()).trim();
    if(!content)throw new Error(`${file.name}: file không có nội dung văn bản.`);
    return content.slice(0,50000);
  }

  const apiKey=getGeminiKey();
  const mime=file.type||(
    lower.endsWith('.pdf')?'application/pdf':
    /\.(png)$/i.test(lower)?'image/png':
    /\.(jpg|jpeg)$/i.test(lower)?'image/jpeg':
    lower.endsWith('.webp')?'image/webp':
    lower.endsWith('.mp3')?'audio/mpeg':
    lower.endsWith('.wav')?'audio/wav':
    lower.endsWith('.m4a')?'audio/mp4':
    lower.endsWith('.ogg')?'audio/ogg':
    'audio/webm'
  );
  const data=await callGemini(apiKey,{
    contents:[{role:'user',parts:[
      {text:'Hãy trích xuất nội dung học tập từ tài liệu này thật trung thực. Giữ nguyên thuật ngữ, tiêu đề, ý chính, số liệu và cấu trúc quan trọng. Với ảnh/PDF hãy đọc chữ; với audio hãy chép lại lời nói. Không tự bổ sung kiến thức ngoài tài liệu. Chỉ trả về phần nội dung đã trích xuất, không viết lời mở đầu.'},
      {inlineData:{mimeType:mime,data:await fileToBase64(file)}}
    ]}],
    generationConfig:{temperature:0,maxOutputTokens:8192}
  });
  const content=geminiText(data);
  if(!content)throw new Error(`${file.name}: AI chưa trích xuất được nội dung.`);
  return content.slice(0,50000);
}

export async function demoChat(lesson:Lesson, question:string, mode:TutorMode):Promise<ChatMessage> {
  if(!question.trim()||question.length>4000)throw new Error('Câu hỏi không hợp lệ.');
  if(typeof window==='undefined')throw new Error('AI Tutor chỉ hoạt động trên trình duyệt.');

  const apiKey=getGeminiKey();

  const modeGuide=mode==='easy'
    ?'Giải thích thật dễ hiểu, dùng ví dụ gần gũi và tránh thuật ngữ không cần thiết.'
    :mode==='advanced'
      ?'Giải thích chuyên sâu, phân tích cơ chế, liên hệ kiến thức và nêu các điểm dễ nhầm.'
      :'Giải thích cân bằng giữa khái niệm, ví dụ và cách áp dụng.';

  const sourceText=lesson.documents
    .filter(d=>d.transcript?.trim())
    .map(d=>`### ${d.name}\n${d.transcript}`)
    .join('\n\n')
    .slice(0,30000);

  const context=[
    `Tên bài học: ${lesson.title}`,
    `Chủ đề: ${lesson.topic}`,
    lesson.description?`Mô tả: ${lesson.description}`:'',
    sourceText?`Tài liệu/nghi chú hiện có:\n${sourceText}`:''
  ].filter(Boolean).join('\n\n');

  const body={
    systemInstruction:{parts:[{text:'Bạn là AI Tutor của AI Study Assistant. Chỉ trả lời dựa trên nội dung tài liệu/nghi chú đã được tải vào bài học. Giữ đúng thuật ngữ, số liệu và cách diễn đạt của tài liệu. Nếu tài liệu không đủ để trả lời, hãy nói rõ rằng tài liệu chưa cung cấp thông tin đó; không tự bổ sung bằng kiến thức ngoài.'}]},
    contents:[{role:'user',parts:[{text:`${modeGuide}\n\nNgữ cảnh bài học:\n${context}\n\nCâu hỏi của sinh viên:\n${question.trim()}`}]}],
    generationConfig:{temperature:0.4,maxOutputTokens:2048}
  };

  if(!sourceText)throw new Error('Bài học chưa có tài liệu đã được AI đọc. Hãy tải tài liệu lên trước.');
  const data=await callGemini(apiKey,body);
  const content=geminiText(data);
  if(!content)throw new Error('Gemini chưa trả về nội dung.');

  const sources=lesson.documents
    .filter(d=>d.transcript?.trim())
    .map(d=>({id:d.id,name:d.name}));

  return {id:uid('message'),role:'assistant',content,sources};
}
export async function demoQuiz(lesson:Lesson, answers:Record<string,string>):Promise<QuizResult> {
  const questions=getLearningBundle(lesson).quiz.questions;
  if(Object.keys(answers).length!==questions.length||questions.some(q=>!q.options.includes(answers[q.id])))
    throw new Error('Cần chọn đủ đáp án hợp lệ.');
  const details=questions.map(q=>({questionId:q.id,selected:answers[q.id],correct:q.answer,
    isCorrect:answers[q.id]===q.answer,explanation:q.explanation}));
  const correctAnswers=details.filter(d=>d.isCorrect).length;
  return {id:uid('result'),completedAt:new Date().toISOString(),scorePercentage:Math.round(correctAnswers/questions.length*100),
    correctAnswers,totalQuestions:questions.length,details};
}
