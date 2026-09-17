import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fator_r.domain.fator_r import Politica
from fator_r.repositories.orm import Firm


async def obter(session: AsyncSession, firm_id: uuid.UUID) -> Firm:
    firm = (await session.execute(select(Firm).where(Firm.id == firm_id))).scalar_one()
    return firm


def politica_de(firm: Firm) -> Politica:
    return Politica(
        cpp_das_integra_fs12=firm.cpp_das_integra_fs12, meta_operacional=firm.meta_operacional
    )
