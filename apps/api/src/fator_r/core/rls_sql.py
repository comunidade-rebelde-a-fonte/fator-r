"""SQL de isolamento por escritório, reutilizado pelas migrações.

A role da aplicação (APP_ROLE) não é dona das tabelas e não tem BYPASSRLS,
então as policies abaixo valem para toda consulta da api.
"""

APP_ROLE = "fator_r_app"
FIRM_SETTING = "nullif(current_setting('app.firm_id', true), '')::uuid"


def enable_rls(table: str, column: str = "firm_id") -> list[str]:
    policy = f"{table}_isolamento_escritorio"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy} ON {table}",
        (
            f"CREATE POLICY {policy} ON {table} TO {APP_ROLE} "
            f"USING ({column} = {FIRM_SETTING}) WITH CHECK ({column} = {FIRM_SETTING})"
        ),
    ]


def grant_app(table: str, privileges: str = "SELECT, INSERT, UPDATE") -> str:
    return f"GRANT {privileges} ON {table} TO {APP_ROLE}"
