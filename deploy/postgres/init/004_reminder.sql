BEGIN;

CREATE INDEX IF NOT EXISTS idx_reminders_user_origin_due
    ON reminders (user_id, unified_msg_origin, trigger_time)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_reminders_processing
    ON reminders (updated_at)
    WHERE status = 'processing';

COMMIT;

