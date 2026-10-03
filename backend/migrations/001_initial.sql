CREATE TABLE users (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL COLLATE NOCASE UNIQUE,
 password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE lessons (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX ix_lessons_user ON lessons(user_id, created_at);
CREATE TABLE documents (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 filename TEXT NOT NULL, storage_name TEXT NOT NULL, media_type TEXT NOT NULL,
 size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, status TEXT NOT NULL
 CHECK(status IN ('pending','processing','ready','failed')),
 content TEXT NOT NULL DEFAULT '', error_code TEXT, source_mode TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(lesson_id, sha256)
);
CREATE INDEX ix_documents_lesson ON documents(lesson_id);
CREATE TABLE transcripts (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 document_id TEXT NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
 content TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE summaries (
 lesson_id TEXT PRIMARY KEY REFERENCES lessons(id) ON DELETE CASCADE,
 summary TEXT NOT NULL, key_points TEXT NOT NULL, source_mode TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE chats (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 question TEXT NOT NULL, answer TEXT NOT NULL, sources TEXT NOT NULL,
 source_mode TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX ix_chats_lesson ON chats(lesson_id, created_at);
CREATE TABLE flashcards (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 question TEXT NOT NULL, answer TEXT NOT NULL, difficulty TEXT NOT NULL,
 source_mode TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE flashcard_reviews (
 id TEXT PRIMARY KEY, flashcard_id TEXT NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 rating TEXT NOT NULL CHECK(rating IN ('again','hard','good','easy')), created_at TEXT NOT NULL
);
CREATE TABLE quizzes (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
 questions TEXT NOT NULL, source_mode TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX ix_quizzes_lesson ON quizzes(lesson_id, created_at);
CREATE TABLE quiz_attempts (
 id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 answers TEXT NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL,
 score REAL NOT NULL CHECK(score >= 0 AND score <= 100), feedback TEXT NOT NULL,
 source_mode TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX ix_attempts_user ON quiz_attempts(user_id, created_at);
