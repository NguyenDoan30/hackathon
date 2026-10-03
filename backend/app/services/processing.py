import logging
from ..security import now, uid
from ..schemas import ProcessedFile
from ..errors import ApiError
from .content import provider_output

log = logging.getLogger(__name__)

def process_document(db, providers, document_id):
    with db.session() as conn:
        changed = conn.execute("UPDATE documents SET status='processing',error_code=NULL,updated_at=? WHERE id=? AND status='pending'", (now(),document_id)).rowcount
        if not changed:
            return
        row = conn.execute('SELECT * FROM documents WHERE id=?', (document_id,)).fetchone()
        document = dict(row)
    try:
        result = provider_output(ProcessedFile, providers.call('file','process',db.uploads / document['storage_name'],document['media_type']))
        with db.session() as conn:
            updated = conn.execute("UPDATE documents SET content=?,status='ready',updated_at=? WHERE id=? AND status='processing'", (result['content'],now(),document_id)).rowcount
            if updated and result.get('transcript'):
                conn.execute('INSERT INTO transcripts VALUES (?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET content=excluded.content', (uid(),document['lesson_id'],document_id,result['transcript'],now()))
    except Exception as exc:
        log.exception('Document processing failed: %s', document_id)
        code = exc.code if isinstance(exc,ApiError) else 'PROCESSING_FAILED'
        with db.session() as conn:
            conn.execute("UPDATE documents SET status='failed',error_code=?,updated_at=? WHERE id=? AND status='processing'", (code,now(),document_id))
