from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from app.main import create_app
from app.config import Settings
from app.integrations.providers import Providers
from app.integrations.demo import DemoAI,DemoFile,DemoLearning
from app.security import now,digest

@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(mode='demo',data_dir=tmp_path))
    with TestClient(app) as client:
        yield client

def register(client,email='alice@example.com'):
    response=client.post('/auth/register',json={'name':'Alice','email':email,'password':'SecureStudy!2026'})
    assert response.status_code==201,response.text
    return response.json()

def auth(session):
    return {'Authorization':'Bearer '+session['access_token']}

def lesson(client,headers,title='OOP'):
    response=client.post('/lessons',json={'title':title},headers=headers)
    assert response.status_code==201,response.text
    return response.json()['id']

def upload(client,headers,lesson_id,content=b'Class is a blueprint. Polymorphism is many forms.',name='notes.md'):
    return client.post('/upload',data={'lesson_id':lesson_id},files={'file':(name,content,'text/markdown')},headers=headers)

def ready_lesson(client):
    headers=auth(register(client))
    lesson_id=lesson(client,headers)
    response=upload(client,headers,lesson_id)
    assert response.status_code==202,response.text
    document=response.json()['id']
    assert client.get('/documents/'+document,headers=headers).json()['status']=='ready'
    return headers,lesson_id,document

def test_auth_password_hash_and_revocation(client):
    session=register(client)
    headers=auth(session)
    assert 'password' not in str(session)
    with client.app.state.db.session() as conn:
        row=conn.execute('SELECT password_hash FROM users WHERE id=?',(session['user']['id'],)).fetchone()
        assert row[0].startswith('$argon2')
        assert conn.execute('SELECT token_hash FROM sessions WHERE user_id=?',(session['user']['id'],)).fetchone()[0]!=session['access_token']
    assert client.get('/auth/me',headers=headers).status_code==200
    assert client.post('/auth/logout',headers=headers).status_code==204
    assert client.get('/auth/me',headers=headers).status_code==401
    assert client.post('/auth/login',json={'email':'alice@example.com','password':'wrong'}).status_code==401
    assert client.post('/auth/login',json={'email':'ALICE@example.com','password':'SecureStudy!2026'}).status_code==200
    assert client.post('/auth/register',json={'name':'Other','email':'ALICE@example.com','password':'SecureStudy!2026'}).status_code==409

def test_expired_session(client):
    session=register(client)
    with client.app.state.db.session() as conn:
        conn.execute('UPDATE sessions SET expires_at=? WHERE token_hash=?',('2000-01-01',digest(session['access_token'])))
    assert client.get('/lessons',headers=auth(session)).status_code==401

def test_validation_never_echoes_password(client):
    response=client.post('/auth/register',json={'name':'','email':'bad','password':'secret'})
    assert response.status_code==422
    assert 'secret' not in response.text
    assert response.json()['error']['code']=='VALIDATION_ERROR'
    assert response.json()['request_id']==response.headers['X-Request-ID']
    assert client.post('/lessons',json={'title':'X'}).status_code==401

def test_lesson_crud_pagination_literal_search(client):
    headers=auth(register(client))
    lid=lesson(client,headers,'SQL 100%')
    lesson(client,headers,'Python')
    page=client.get('/lessons?limit=1&offset=1',headers=headers).json()
    assert page['total']==2 and len(page['items'])==1
    assert client.get('/lessons?q=%25',headers=headers).json()['total']==1
    assert client.get('/lessons?limit=0',headers=headers).status_code==422
    assert client.patch('/lessons/'+lid,json={'title':'  Updated  '},headers=headers).json()['title']=='Updated'
    assert client.patch('/lessons/'+lid,json={'title':None},headers=headers).status_code==422
    assert client.post('/lessons',json={'title':'   '},headers=headers).status_code==422
    assert client.delete('/lessons/'+lid,headers=headers).status_code==204
    assert client.get('/lessons/'+lid,headers=headers).status_code==404

def test_complete_backend_workflow(client):
    headers,lid,doc=ready_lesson(client)
    summary=client.post(f'/summary/{lid}/generate',headers=headers)
    assert summary.status_code==200 and summary.json()['source_mode']=='demo'
    assert client.get(f'/summary/{lid}',headers=headers).json()['key_points']
    reply=client.post('/chat',json={'lesson_id':lid,'question':'Explain polymorphism'},headers=headers)
    assert reply.status_code==201 and reply.json()['sources']==[doc]
    assert client.get('/chat/'+lid,headers=headers).json()['total']==1
    cards=client.post('/flashcards/'+lid+'/generate',headers=headers).json()['items']
    assert len(cards)==4
    assert client.post('/flashcards/'+cards[0]['id']+'/review',json={'rating':'good'},headers=headers).status_code==201
    quiz=client.post('/quiz/'+lid+'/generate',headers=headers).json()
    for q in quiz['questions']:
        assert set(q)=={'id','question','options'}
    answers={'q1':'Một thể hiện của class','q2':'Đóng gói','q3':'Đa hình'}
    result=client.post('/quizzes/'+quiz['id']+'/submit',json={'answers':answers},headers=headers)
    assert result.status_code==201 and result.json()['score']==100
    assert result.json()['correct']==3
    progress=client.get('/progress/'+lid,headers=headers).json()
    assert progress['attempts']==1 and progress['best_score']==100
    assert progress['flashcard_reviews']==1
    assert client.get('/documents/'+doc+'/download',headers=headers).content.startswith(b'Class')

@pytest.mark.parametrize('target',[
 ('GET','/lessons/{lid}'),('PATCH','/lessons/{lid}'),('DELETE','/lessons/{lid}'),
 ('GET','/documents/{doc}'),('GET','/documents/{doc}/download'),('DELETE','/documents/{doc}'),('POST','/documents/{doc}/retry'),
 ('GET','/summary/{lid}'),('POST','/summary/{lid}/generate'),('GET','/chat/{lid}'),
 ('GET','/flashcards/{lid}'),('POST','/flashcards/{lid}/generate'),('GET','/quiz/{lid}'),('POST','/quiz/{lid}/generate'),('GET','/progress/{lid}')])
def test_cross_account_access_denied(client,target):
    owner,lid,doc=ready_lesson(client)
    stranger=auth(register(client,'bob@example.com'))
    method,path=target
    kwargs={'headers':stranger}
    if method=='PATCH':kwargs['json']={'title':'Hacked'}
    response=client.request(method,path.format(lid=lid,doc=doc),**kwargs)
    assert response.status_code==404,response.text
    assert client.get('/lessons',headers=stranger).json()['total']==0

def test_cross_account_chat_upload_review_and_submit(client):
    owner,lid,doc=ready_lesson(client)
    card=client.post('/flashcards/'+lid+'/generate',headers=owner).json()['items'][0]
    quiz=client.post('/quiz/'+lid+'/generate',headers=owner).json()
    stranger=auth(register(client,'bob@example.com'))
    assert upload(client,stranger,lid).status_code==404
    assert client.post('/chat',json={'lesson_id':lid,'question':'hello'},headers=stranger).status_code==404
    assert client.post('/flashcards/'+card['id']+'/review',json={'rating':'easy'},headers=stranger).status_code==404
    assert client.post('/quizzes/'+quiz['id']+'/submit',json={'answers':{}},headers=stranger).status_code==404

@pytest.mark.parametrize('name,content,status,code',[
 ('empty.md',b'',422,'EMPTY_FILE'),('program.exe',b'hello',415,'UNSUPPORTED_FILE'),
 ('bad.pdf',b'not a pdf',415,'FILE_CONTENT_MISMATCH'),('bad.txt',b'\xff\xfe',415,'FILE_CONTENT_MISMATCH'),
 ('blank.md',b'  \n',415,'FILE_CONTENT_MISMATCH'),('evil.png',b'not an image',415,'FILE_CONTENT_MISMATCH')])
def test_invalid_uploads_leave_no_files(client,name,content,status,code):
    headers=auth(register(client));lid=lesson(client,headers)
    before=set(client.app.state.db.uploads.iterdir())
    response=upload(client,headers,lid,content,name)
    assert response.status_code==status and response.json()['error']['code']==code
    assert set(client.app.state.db.uploads.iterdir())==before

def test_duplicate_upload_and_safe_filename(client):
    headers,lid,doc=ready_lesson(client)
    duplicate=upload(client,headers,lid)
    assert duplicate.status_code==409
    path_upload=upload(client,headers,lid,b'Safe text with unique content','../../outside.md')
    assert path_upload.status_code==202 and path_upload.json()['filename']=='outside.md'
    with client.app.state.db.session() as conn:
        row=conn.execute('SELECT storage_name FROM documents WHERE id=?',(path_upload.json()['id'],)).fetchone()
        assert '..' not in row[0] and '/' not in row[0]

def test_oversized_upload_cleans_up(tmp_path):
    with TestClient(create_app(Settings(mode='demo',data_dir=tmp_path,max_upload_mb=1))) as client:
        headers=auth(register(client));lid=lesson(client,headers)
        before=set(client.app.state.db.uploads.iterdir())
        response=upload(client,headers,lid,b'a'*(1024*1024+1))
        assert response.status_code==413
        assert set(client.app.state.db.uploads.iterdir())==before

def test_empty_context_and_invalid_quiz_answers(client):
    headers=auth(register(client));lid=lesson(client,headers)
    assert client.post('/summary/'+lid+'/generate',headers=headers).status_code==409
    assert client.post('/chat',json={'lesson_id':lid,'question':'hello'},headers=headers).status_code==409
    upload(client,headers,lid)
    quiz=client.post('/quiz/'+lid+'/generate',headers=headers).json()
    for answers in ({},{'q1':'not an option'},{'q1':'x','q2':'x','q3':'x','q4':'x'}):
        assert client.post('/quizzes/'+quiz['id']+'/submit',json={'answers':answers},headers=headers).status_code==422
    assert client.get('/progress/'+lid,headers=headers).json()['attempts']==0

def test_provider_failures_and_invalid_sources_do_not_persist(client):
    headers,lid,doc=ready_lesson(client)
    class BadAI:
        def chat(self,*args):return {'answer':'Bad answer','sources':['other-tenant-document']}
        def summarize(self,*args):raise RuntimeError('private secret internal error')
    client.app.state.providers.ai=BadAI()
    response=client.post('/chat',json={'lesson_id':lid,'question':'hello'},headers=headers)
    assert response.status_code==502
    assert client.get('/chat/'+lid,headers=headers).json()['total']==0
    response=client.post('/summary/'+lid+'/generate',headers=headers)
    assert response.status_code==502 and 'private secret' not in response.text

def test_invalid_learning_output_atomic_replacement(client):
    headers,lid,doc=ready_lesson(client)
    before=client.post('/flashcards/'+lid+'/generate',headers=headers).json()['items']
    class BadLearning(DemoLearning):
        def flashcards(self,*args):return [{'question':'x','answer':''}]
        def quiz(self,*args):return [dict(super().quiz(*args)[0],answer='not an option')]
    client.app.state.providers.learning=BadLearning()
    assert client.post('/flashcards/'+lid+'/generate',headers=headers).status_code==502
    assert client.get('/flashcards/'+lid,headers=headers).json()['items']==before
    assert client.post('/quiz/'+lid+'/generate',headers=headers).status_code==502

def test_production_never_seeds_or_falls_back(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path))) as client:
        assert client.get('/demo').status_code==404
        health=client.get('/health').json()
        assert health['mode']=='production'
        assert all(v=='not_connected' for v in health['integrations'].values())
        with client.app.state.db.session() as conn:assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
        headers=auth(register(client));lid=lesson(client,headers)
        response=upload(client,headers,lid)
        document=client.get('/documents/'+response.json()['id'],headers=headers).json()
        assert document['status']=='failed' and document['error_code']=='PROVIDER_UNAVAILABLE'
        client.app.state.providers.file=DemoFile() # Explicit test injection, not a fallback.
        assert client.post('/documents/'+document['id']+'/retry',headers=headers).status_code==202
        assert client.get('/documents/'+document['id'],headers=headers).json()['status']=='ready'
        assert client.post('/summary/'+lid+'/generate',headers=headers).status_code==503

def test_persistence_and_idempotent_migrations(tmp_path):
    settings=Settings(mode='demo',data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        headers,lid,doc=ready_lesson(client)
        client.post('/chat',json={'lesson_id':lid,'question':'Persist this'},headers=headers)
    with TestClient(create_app(settings)) as client:
        assert client.get('/lessons/'+lid,headers=headers).status_code==200
        assert client.get('/chat/'+lid,headers=headers).json()['total']==1
        assert client.get('/documents/'+doc+'/download',headers=headers).status_code==200
        with client.app.state.db.session() as conn:
            assert conn.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0]==1
            assert conn.execute('PRAGMA foreign_keys').fetchone()[0]==1
            assert conn.execute('PRAGMA journal_mode').fetchone()[0]=='wal'

def test_cascade_deletion_and_file_cleanup(client):
    headers,lid,doc=ready_lesson(client)
    client.post('/summary/'+lid+'/generate',headers=headers)
    client.post('/chat',json={'lesson_id':lid,'question':'hello'},headers=headers)
    client.post('/flashcards/'+lid+'/generate',headers=headers)
    quiz=client.post('/quiz/'+lid+'/generate',headers=headers).json()
    client.post('/quizzes/'+quiz['id']+'/submit',json={'answers':{q['id']:q['options'][0] for q in quiz['questions']}},headers=headers)
    with client.app.state.db.session() as conn:storage=conn.execute('SELECT storage_name FROM documents WHERE id=?',(doc,)).fetchone()[0]
    assert client.delete('/lessons/'+lid,headers=headers).status_code==204
    assert not (client.app.state.db.uploads/storage).exists()
    with client.app.state.db.session() as conn:
        for table in ('documents','summaries','chats','flashcards','quizzes'):
            assert conn.execute(f'SELECT COUNT(*) FROM {table} WHERE lesson_id=?',(lid,)).fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM quiz_attempts WHERE quiz_id=?',(quiz['id'],)).fetchone()[0]==0

def test_concurrent_writes(client):
    headers=auth(register(client))
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda i:client.post('/lessons',json={'title':f'Parallel {i}'},headers=headers),range(15)))
    assert all(r.status_code==201 for r in results)
    assert client.get('/lessons',headers=headers).json()['total']==15

def test_cors_and_demo_assets(client):
    assert client.get('/demo').status_code==200
    assert client.get('/demo/assets/app.js').status_code==200
    allowed=client.options('/lessons',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
    assert allowed.headers['access-control-allow-origin']=='http://localhost:3000'
    denied=client.options('/lessons',headers={'Origin':'https://unapproved.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in denied.headers
