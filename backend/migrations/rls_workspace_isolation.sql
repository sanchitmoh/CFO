-- ═══════════════════════════════════════════════════════════════════
-- ADVANCE-004: Row-Level Security for Multi-Tenant Isolation
-- ═══════════════════════════════════════════════════════════════════
-- Defense-in-depth: even if application code forgets a workspace_id
-- filter, the database itself rejects rows from other workspaces.
--
-- PREREQUISITE: The app must SET app.workspace_id = '<uuid>' at the
-- start of each DB session (see database.py middleware).
-- ═══════════════════════════════════════════════════════════════════

-- All tenant-scoped tables (workspaces and industry_benchmarks excluded —
-- workspaces is the root, benchmarks are global reference data).

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'transactions',
            'budgets',
            'goals',
            'alerts',
            'alert_rules',
            'chat_sessions',
            'chat_messages',
            'forecast_results',
            'audit_logs'
        ])
    LOOP
        -- Enable RLS (idempotent)
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

        -- Force RLS even for table owners (prevents superuser bypass in app context)
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', tbl);

        -- Drop existing policy if re-running
        EXECUTE format('DROP POLICY IF EXISTS workspace_isolation ON %I', tbl);

        -- Create isolation policy: rows visible only when workspace_id matches session var
        EXECUTE format(
            'CREATE POLICY workspace_isolation ON %I
                USING (workspace_id = current_setting(''app.workspace_id'')::UUID)
                WITH CHECK (workspace_id = current_setting(''app.workspace_id'')::UUID)',
            tbl
        );
    END LOOP;
END;
$$;

-- Users table is special: isolated by workspace_id but also needs self-access
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workspace_isolation ON users;
CREATE POLICY workspace_isolation ON users
    USING (workspace_id = current_setting('app.workspace_id')::UUID)
    WITH CHECK (workspace_id = current_setting('app.workspace_id')::UUID);

-- ═══════════════════════════════════════════════════════════════════
-- VERIFY: List all RLS policies
-- ═══════════════════════════════════════════════════════════════════
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies WHERE schemaname = 'public';
