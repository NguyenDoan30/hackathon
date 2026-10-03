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
    &&['ready','pending','processing','failed'].includes(String(d.status))&&d.sourceMode==='demo'
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
export async function demoChat(lesson:Lesson, question:string, mode:TutorMode):Promise<ChatMessage> {
  if(!question.trim()||question.length>4000)throw new Error('Câu hỏi không hợp lệ.');
  const bundle=getLearningBundle(lesson);
  const lead=mode==='easy'?'Cùng bắt đầu từ ý đơn giản:':mode==='advanced'?'Các ý để bạn phân tích thêm:':'Những ý chính trong bài mẫu:';
  const detail=mode==='easy'?bundle.summary.keyPoints[0]:bundle.summary.keyPoints.join('\n• ');
  return {id:uid('message'),role:'assistant',content:`[Phản hồi mẫu — không phải AI thật]\n${lead}\n${detail}\n\nĐây là phản hồi minh họa theo bài mẫu, không phân tích câu hỏi hoặc file đã chọn.`,
    sources:Object.hasOwn(learningFixtures,lesson.id)?lesson.documents.filter(d=>d.id===`${lesson.id}-document`).map(d=>({id:d.id,name:d.name})):[]};
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
