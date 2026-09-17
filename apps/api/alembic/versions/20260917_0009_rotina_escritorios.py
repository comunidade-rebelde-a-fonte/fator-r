"""função de sistema para a rotina semanal do priorizador (T-611)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-17

A rotina roda sem usuário e sem escritório no contexto; só precisa dos ids dos escritórios.
"""

from collections.abc import Sequence

from alembic import op

from fator_r.core.rls_sql import APP_ROLE

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION rotina_escritorios()
        RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT id FROM firms ORDER BY criado_em $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION rotina_escritorios() FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION rotina_escritorios() TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS rotina_escritorios()")
