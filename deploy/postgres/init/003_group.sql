BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS idx_quotes_unique_source
    ON quotes (group_id, source_message_id)
    WHERE source_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_group_user_created
    ON messages (group_id, user_id, created_at DESC)
    WHERE is_bot = FALSE;

COMMIT;

