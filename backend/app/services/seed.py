import json
from ..security import uid,now,hasher
from ..integrations.demo import DEMO_TEXT

EMAIL='demo@studyassistant.dev'
PASSWORD='DemoStudy!2026'

def seed_demo(db,providers):
    with db.session() as conn:
        if conn.execute('SELECT 1 FROM users WHERE email=?',(EMAIL,)).fetchone():
            return
        user_id,lesson_id,document_id=uid(),uid(),uid()
        timestamp=now()
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?)',(user_id,'Nguyễn Minh An',EMAIL,hasher.hash(PASSWORD),timestamp))
        conn.execute('INSERT INTO lessons VALUES (?,?,?,?,?,?)',(lesson_id,user_id,'Lập trình hướng đối tượng','Class, object và bốn nguyên lý OOP',timestamp,timestamp))
        second=uid()
        conn.execute('INSERT INTO lessons VALUES (?,?,?,?,?,?)',(second,user_id,'Cơ sở dữ liệu quan hệ','Bài học trống để thử upload và tạo nội dung',timestamp,timestamp))
        storage=document_id+'.md'
        path=db.uploads/storage
        path.write_text(DEMO_TEXT,encoding='utf-8')
        import hashlib
        conn.execute('INSERT INTO documents(id,lesson_id,filename,storage_name,media_type,size_bytes,sha256,status,content,source_mode,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(document_id,lesson_id,'oop-notes.md',storage,'text/markdown',path.stat().st_size,hashlib.sha256(path.read_bytes()).hexdigest(),'ready',DEMO_TEXT,'demo',timestamp,timestamp))
        context=[{'id':document_id,'filename':'oop-notes.md','content':DEMO_TEXT}]
        summary=providers.ai.summarize(context)
        conn.execute('INSERT INTO summaries VALUES (?,?,?,?,?)',(lesson_id,summary['summary'],json.dumps(summary['key_points'],ensure_ascii=False),'demo',timestamp))
        for card in providers.learning.flashcards(context):
            conn.execute('INSERT INTO flashcards VALUES (?,?,?,?,?,?,?)',(uid(),lesson_id,card['question'],card['answer'],card['difficulty'],'demo',timestamp))
        quiz_id=uid()
        questions=providers.learning.quiz(context)
        conn.execute('INSERT INTO quizzes VALUES (?,?,?,?,?)',(quiz_id,lesson_id,json.dumps(questions,ensure_ascii=False),'demo',timestamp))
        answers={q['id']:q['options'][0] for q in questions}
        grade=providers.learning.grade(questions,answers)
        conn.execute('INSERT INTO quiz_attempts VALUES (?,?,?,?,?,?,?,?,?,?)',(uid(),quiz_id,user_id,json.dumps(answers),grade['correct'],grade['total'],grade['score'],json.dumps(grade['feedback'],ensure_ascii=False),'demo',timestamp))
