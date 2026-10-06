BEGIN;

CREATE INDEX IF NOT EXISTS idx_memories_user_scope_updated
    ON memories (user_id, group_id, importance DESC, updated_at DESC);

COMMIT;

