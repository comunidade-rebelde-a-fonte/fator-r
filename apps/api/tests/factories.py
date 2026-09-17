import uuid
from dataclasses import dataclass
from decimal import Decimal

import httpx

from fator_r.core.db import get_owner_sessionmaker
from fator_r.core.security import hash_password
from fator_r.repositories.orm import Firm, User

SENHA_PADRAO = "senha-de-teste-123"


@dataclass(frozen=True)
class UsuarioCriado:
    firm_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    senha: str


async def criar_escritorio_com_usuario(
    email: str = "analista@escritorio-a.com.br", ativo: bool = True
) -> UsuarioCriado:
    async with get_owner_sessionmaker()() as session:
        firm = Firm(
            nome="Escritório de teste",
            meta_operacional=Decimal("0.30"),
            limiar_confianca_parser=Decimal("0.40"),
            piso_economia_anual=Decimal("6000.00"),
            cpp_das_integra_fs12=False,
            tolerancia_ouro_pct=Decimal("0.01"),
        )
        session.add(firm)
        await session.flush()
        user = User(
            firm_id=firm.id,
            email=email,
            senha_hash=hash_password(SENHA_PADRAO),
            nome="Analista",
            ativo=ativo,
        )
        session.add(user)
        await session.commit()
        return UsuarioCriado(firm.id, user.id, email, SENHA_PADRAO)


async def login(client: "httpx.AsyncClient", usuario: UsuarioCriado) -> None:
    response = await client.post(
        "/auth/login", json={"email": usuario.email, "senha": usuario.senha}
    )
    assert response.status_code == 200, response.text


def empresa_payload(cnpj: str = "11.222.333/0001-81", **extra: object) -> dict[str, object]:
    return {
        "nome": "Clínica Exemplo Ltda",
        "cnpj": cnpj,
        "sujeita_fator_r": True,
        "pacote": "monitoramento",
        "honorario_mensal": "450.00",
        **extra,
    }
