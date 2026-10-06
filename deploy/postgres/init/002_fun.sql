BEGIN;

CREATE TABLE IF NOT EXISTS lotteries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id TEXT NOT NULL,
    unified_msg_origin TEXT NOT NULL,
    prize TEXT NOT NULL,
    winner_count INTEGER NOT NULL CHECK (winner_count BETWEEN 1 AND 20),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'drawn', 'cancelled')),
    created_by TEXT NOT NULL,
    drawn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lottery_entries (
    id BIGSERIAL PRIMARY KEY,
    lottery_id UUID NOT NULL REFERENCES lotteries(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    nickname TEXT,
    won BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lottery_id, user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_lotteries_one_open_per_group
    ON lotteries (group_id) WHERE status = 'open';
CREATE INDEX IF NOT EXISTS idx_lotteries_group_created
    ON lotteries (group_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lottery_entries_lottery
    ON lottery_entries (lottery_id, joined_at);

DROP TRIGGER IF EXISTS lotteries_set_updated_at ON lotteries;
CREATE TRIGGER lotteries_set_updated_at BEFORE UPDATE ON lotteries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS lottery_entries_set_updated_at ON lottery_entries;
CREATE TRIGGER lottery_entries_set_updated_at BEFORE UPDATE ON lottery_entries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;

