BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    nickname TEXT,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE groups (
    id BIGSERIAL PRIMARY KEY,
    group_id TEXT NOT NULL UNIQUE,
    name TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    nickname TEXT,
    group_id TEXT,
    message_type TEXT NOT NULL CHECK (message_type IN ('private', 'group')),
    content TEXT NOT NULL,
    is_bot BOOLEAN NOT NULL DEFAULT FALSE,
    raw_event JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT messages_platform_identity UNIQUE (message_type, message_id)
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    group_id TEXT,
    session_key TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    model TEXT,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memories (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    group_id TEXT,
    memory_type TEXT NOT NULL DEFAULT 'explicit',
    content TEXT NOT NULL,
    importance SMALLINT NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    group_id TEXT,
    unified_msg_origin TEXT NOT NULL,
    content TEXT NOT NULL,
    trigger_time TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'sent', 'cancelled', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE quotes (
    id BIGSERIAL PRIMARY KEY,
    source_message_id TEXT,
    user_id TEXT NOT NULL,
    nickname TEXT,
    group_id TEXT NOT NULL,
    content TEXT NOT NULL,
    quoted_at TIMESTAMPTZ,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_uri TEXT,
    content_sha256 CHAR(64) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (content_sha256)
);

-- 默认按 1536 维设计；更换 Embedding 模型时应新增迁移，而不是在线修改。
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    embedding vector(1536),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE plugin_configs (
    id BIGSERIAL PRIMARY KEY,
    plugin_name TEXT NOT NULL,
    scope_type TEXT NOT NULL DEFAULT 'global'
        CHECK (scope_type IN ('global', 'group', 'user')),
    scope_id TEXT NOT NULL DEFAULT '*',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (plugin_name, scope_type, scope_id)
);

CREATE TABLE llm_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    group_id TEXT,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
    completion_tokens INTEGER NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
    total_tokens INTEGER GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,
    request_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_group_created ON messages (group_id, created_at DESC);
CREATE INDEX idx_messages_user_created ON messages (user_id, created_at DESC);
CREATE INDEX idx_messages_created ON messages (created_at DESC);
CREATE INDEX idx_conversations_session_created ON conversations (session_key, created_at DESC);
CREATE INDEX idx_conversations_scope_created ON conversations (group_id, user_id, created_at DESC);
CREATE INDEX idx_memories_scope ON memories (user_id, group_id, importance DESC);
CREATE INDEX idx_reminders_due ON reminders (trigger_time) WHERE status = 'pending';
CREATE INDEX idx_quotes_group_user ON quotes (group_id, user_id);
CREATE INDEX idx_document_chunks_document ON document_chunks (document_id, chunk_index);
CREATE INDEX idx_document_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL;
CREATE INDEX idx_llm_usage_user_created ON llm_usage (user_id, created_at DESC);
CREATE INDEX idx_llm_usage_created ON llm_usage (created_at DESC);

CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER groups_set_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER messages_set_updated_at BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER conversations_set_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER memories_set_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER reminders_set_updated_at BEFORE UPDATE ON reminders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER quotes_set_updated_at BEFORE UPDATE ON quotes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER documents_set_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER document_chunks_set_updated_at BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER plugin_configs_set_updated_at BEFORE UPDATE ON plugin_configs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER llm_usage_set_updated_at BEFORE UPDATE ON llm_usage
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
