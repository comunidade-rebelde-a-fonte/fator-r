"""Modelos ORM. O acesso a eles acontece só pela camada repositories/."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from fator_r.core.models import Base

PACOTES = ("monitoramento", "correcao", "retainer")
ORIGENS = ("manual", "pgdas", "folha", "agente")


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def _criado_em() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Firm(Base):
    __tablename__ = "firms"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(Text)
    meta_operacional: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    limiar_confianca_parser: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    piso_economia_anual: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cpp_das_integra_fs12: Mapped[bool] = mapped_column(Boolean)
    tolerancia_ouro_pct: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    criado_em: Mapped[datetime] = _criado_em()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    senha_hash: Mapped[str] = mapped_column(Text)
    nome: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    criado_em: Mapped[datetime] = _criado_em()


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _criado_em()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("firms.id"))
    nome: Mapped[str] = mapped_column(Text)
    cnpj: Mapped[str] = mapped_column(String(14))
    cnae: Mapped[str | None] = mapped_column(Text)
    atividade: Mapped[str | None] = mapped_column(Text)
    sujeita_fator_r: Mapped[bool] = mapped_column(Boolean)
    qtd_socios: Mapped[int] = mapped_column(Integer, server_default="1")
    contato: Mapped[str | None] = mapped_column(Text)
    pacote: Mapped[str | None] = mapped_column(
        ENUM(*PACOTES, name="pacote_comercial", create_type=False)
    )
    honorario_mensal: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    ativo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    notas: Mapped[str | None] = mapped_column(Text)
    inicio_atividade: Mapped[date | None] = mapped_column(Date)
    criado_em: Mapped[datetime] = _criado_em()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MonthlyMovement(Base):
    __tablename__ = "monthly_movements"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    competencia: Mapped[date] = mapped_column(Date)
    receita_bruta: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    pro_labore: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    salarios: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    cpp: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    fgts: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    folha_mes: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), Computed("pro_labore + salarios + cpp + fgts", persisted=True)
    )
    origem: Mapped[str] = mapped_column(ENUM(*ORIGENS, name="origem_movimento", create_type=False))
    observacao: Mapped[str | None] = mapped_column(Text)
    pgdas_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    criado_em: Mapped[datetime] = _criado_em()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SimplesTable(Base):
    __tablename__ = "simples_tables"

    id: Mapped[uuid.UUID] = _uuid_pk()
    anexo: Mapped[str] = mapped_column(ENUM("III", "V", name="anexo_simples", create_type=False))
    faixa: Mapped[int] = mapped_column(SmallInteger)
    rbt12_ate: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    aliquota_nominal: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    parcela_deduzir: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    vigencia_inicio: Mapped[date] = mapped_column(Date)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    agente: Mapped[str] = mapped_column(Text)
    gatilho: Mapped[str] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    entrada_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    saida_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    decisao_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(
        ENUM("ok", "error", "needs_review", name="status_trace", create_type=False)
    )
    confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    langfuse_sync: Mapped[str] = mapped_column(
        ENUM("pending", "ok", "failed", name="langfuse_sync", create_type=False),
        server_default="pending",
    )
    criado_em: Mapped[datetime] = _criado_em()


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    trace_id: Mapped[str] = mapped_column(String(32), ForeignKey("agent_traces.id"))
    agente: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text)
    dados_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = _criado_em()


class EvalGold(Base):
    __tablename__ = "evals_gold"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    trace_id: Mapped[str] = mapped_column(String(32), ForeignKey("agent_traces.id"))
    campo: Mapped[str] = mapped_column(Text)
    esperado: Mapped[str | None] = mapped_column(Text)
    obtido: Mapped[str | None] = mapped_column(Text)
    dentro_tolerancia: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(
        ENUM("ok", "erro", "ouro_indisponivel", name="status_eval_ouro", create_type=False)
    )
    criado_em: Mapped[datetime] = _criado_em()


class EvalHuman(Base):
    __tablename__ = "evals_human"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    trace_id: Mapped[str] = mapped_column(String(32), ForeignKey("agent_traces.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    nota: Mapped[str] = mapped_column(
        ENUM("acerto", "parcial", "erro", name="nota_humana", create_type=False)
    )
    comentario: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = _criado_em()


class PgdasDocument(Base):
    __tablename__ = "pgdas_documents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    arquivo_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    mime: Mapped[str] = mapped_column(Text)
    tamanho_bytes: Mapped[int] = mapped_column(Integer)
    nome_original: Mapped[str | None] = mapped_column(Text)
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    campos_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[str] = mapped_column(
        ENUM(
            "received",
            "parsed",
            "needs_review",
            "linked",
            "rejected",
            name="status_documento",
            create_type=False,
        )
    )
    motivo: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(32), ForeignKey("agent_traces.id"))
    criado_em: Mapped[datetime] = _criado_em()
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    firm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    pa: Mapped[date] = mapped_column(Date)
    parametros_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    resultado_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    veredito: Mapped[str | None] = mapped_column(
        ENUM("ja_na_meta", "corrigir", "nao_forcar", name="veredito_simulacao", create_type=False)
    )
    trace_id: Mapped[str] = mapped_column(String(32), ForeignKey("agent_traces.id"))
    criado_em: Mapped[datetime] = _criado_em()
