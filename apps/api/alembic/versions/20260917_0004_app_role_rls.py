"""role da aplicação, RLS por escritório e funções de autenticação (T-103)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17

- fator_r_app: role usada pela api. Não é dona das tabelas e não tem BYPASSRLS.
  A senha e o LOGIN são definidos por `python -m fator_r.db_roles` (fora do código).
- RLS ativo (sem FORCE): vale para a role da aplicação; a role dona continua sendo
  o caminho explícito de migrações e seed.
- Login acontece antes de o escritório ser conhecido: as funções SECURITY DEFINER
  abaixo devolvem só o mínimo necessário e são o único caminho de leitura de users
  sem app.firm_id.
"""

from collections.abc import Sequence

from alembic import op

from fator_r.core.rls_sql import APP_ROLE, enable_rls, grant_app

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} NOLOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
            END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(grant_app("firms", "SELECT"))
    op.execute(grant_app("users", "SELECT"))
    op.execute(grant_app("sessions", "SELECT, INSERT, DELETE"))
    op.execute(grant_app("companies"))
    op.execute(grant_app("monthly_movements"))

    for statement in enable_rls("firms", column="id"):
        op.execute(statement)
    for table in ("users", "companies", "monthly_movements"):
        for statement in enable_rls(table):
            op.execute(statement)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION auth_find_user(p_email text)
        RETURNS TABLE (id uuid, firm_id uuid, email text, nome text, senha_hash text, ativo boolean)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT u.id, u.firm_id, u.email::text, u.nome, u.senha_hash, u.ativo
            FROM users u WHERE lower(u.email) = lower(p_email)
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION auth_session_user(p_token_hash text)
        RETURNS TABLE (id uuid, firm_id uuid, email text, nome text)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT u.id, u.firm_id, u.email::text, u.nome
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = p_token_hash AND s.expira_em > now() AND u.ativo
        $$;
        """
    )
    for fn in ("auth_find_user(text)", "auth_session_user(text)"):
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS auth_session_user(text)")
    op.execute("DROP FUNCTION IF EXISTS auth_find_user(text)")
    for table in ("monthly_movements", "companies", "users", "firms"):
        op.execute(f"DROP POLICY IF EXISTS {table}_isolamento_escritorio ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON sessions FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
