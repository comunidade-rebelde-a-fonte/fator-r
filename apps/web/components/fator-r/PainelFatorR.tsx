"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { SemaforoBadge } from "@/components/fator-r/SemaforoBadge";
import { Carregando, Erro } from "@/components/ui/Estado";
import { ApiError } from "@/lib/api";
import { obterFatorR } from "@/lib/api/companies";
import type { FatorROut } from "@/lib/api/types";
import {
  competenciaAtual,
  formatarPercentual,
  formatarReais,
  rotuloCompetencia,
  somarMeses,
} from "@/lib/format";

const MOTIVOS: Record<NonNullable<FatorROut["motivo"]>, string> = {
  rbt12_zero: "Sem receita na janela (RBT12 = 0). Lance a receita dos 12 meses anteriores ao PA.",
  empresa_nova_regra_pendente:
    "Empresa com menos de 12 meses na janela. A regra de proporcionalização ainda está em conferência (P-05).",
  rbt12_acima_do_limite_do_simples: "RBT12 acima do limite do Simples Nacional.",
};

function Card({ titulo, valor, testid }: { titulo: string; valor: string; testid?: string }) {
  return (
    <div className="rounded border border-zinc-200 p-3">
      <div className="text-xs text-zinc-500">{titulo}</div>
      <div className="mt-1 text-lg font-semibold" data-testid={testid}>
        {valor}
      </div>
    </div>
  );
}

export function PainelFatorR({ companyId }: { companyId: string }) {
  const [pa, setPa] = useState(competenciaAtual());
  const resultado = useQuery({
    queryKey: ["fator-r", companyId, pa],
    queryFn: () => obterFatorR(companyId, pa),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <label className="flex items-center gap-2">
          Período de apuração (PA)
          <input
            type="month"
            name="pa"
            value={pa}
            onChange={(e) => e.target.value && setPa(e.target.value)}
            className="rounded border border-zinc-300 px-2 py-1"
          />
        </label>
        <button
          type="button"
          onClick={() => setPa(somarMeses(pa, -1))}
          className="rounded border px-2 py-1"
        >
          ← PA anterior
        </button>
        <button
          type="button"
          onClick={() => setPa(somarMeses(pa, 1))}
          className="rounded border px-2 py-1"
        >
          PA seguinte →
        </button>
      </div>

      {resultado.isPending && <Carregando />}
      {resultado.isError && (
        <Erro
          texto={
            resultado.error instanceof ApiError && resultado.error.status === 422
              ? "Não há tabela do Simples vigente para esse PA."
              : "Não foi possível calcular o Fator R."
          }
          onRetry={() => resultado.refetch()}
        />
      )}
      {resultado.isSuccess && <Resultado r={resultado.data} />}
    </div>
  );
}

function Resultado({ r }: { r: FatorROut }) {
  const faltantes = new Set(r.meses_faltantes);
  const preenchidos = new Set(r.meses_preenchidos);
  const meses = Array.from({ length: 12 }, (_, i) => somarMeses(r.janela_inicio, i));

  return (
    <div className="space-y-3" data-testid="painel-fator-r">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <SemaforoBadge semaforo={r.semaforo} />
        <span data-testid="janela">
          Janela: {rotuloCompetencia(r.janela_inicio)} a {rotuloCompetencia(r.janela_fim)}
        </span>
        <span className="text-zinc-500" data-testid="politica-cpp">
          Política do escritório: CPP do DAS {r.cpp_integra_fs12 ? "integra" : "não integra"} a FS12
        </span>
        <span className="text-zinc-500" data-testid="vigencia-tabela">
          Tabelas do Simples vigentes desde{" "}
          {r.tabela_vigencia_inicio.split("-").reverse().join("/")}
        </span>
      </div>

      <div className="flex flex-wrap gap-1" aria-label="Meses da janela">
        {meses.map((m) => {
          const situacao = faltantes.has(m)
            ? "faltante"
            : preenchidos.has(m)
              ? "preenchido"
              : "fora";
          const cor = {
            faltante: "bg-red-100 text-red-800",
            preenchido: "bg-emerald-100 text-emerald-800",
            fora: "bg-zinc-100 text-zinc-500",
          }[situacao];
          return (
            <span
              key={m}
              data-mes={m}
              data-situacao={situacao}
              className={`rounded px-2 py-0.5 text-xs ${cor}`}
            >
              {rotuloCompetencia(m)}
              {situacao === "faltante" ? " · faltante" : ""}
            </span>
          );
        })}
      </div>

      {r.status === "dados_insuficientes" && r.motivo && (
        <div
          data-testid="dados-insuficientes"
          className="rounded border border-zinc-300 bg-zinc-50 p-3 text-sm"
        >
          <strong>Dados insuficientes.</strong> {MOTIVOS[r.motivo]}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card titulo="Fator R" valor={formatarPercentual(r.fator_r)} testid="fator-r" />
        <Card titulo="Anexo" valor={r.anexo ? `Anexo ${r.anexo}` : "—"} testid="anexo" />
        <Card titulo="RBT12" valor={formatarReais(r.rbt12)} testid="rbt12" />
        <Card titulo="FS12" valor={formatarReais(r.fs12)} testid="fs12" />
        <Card titulo="Folha mínima 28% (12 meses)" valor={formatarReais(r.folha_minima_28)} />
        <Card
          titulo={`Folha mínima ${formatarPercentual(r.meta_operacional)} (meta)`}
          valor={formatarReais(r.folha_minima_meta)}
        />
        <Card titulo="Gap até 28% (12 meses)" valor={formatarReais(r.gap_12m_28)} />
        <Card titulo="Reforço mensal até 28%" valor={formatarReais(r.reforco_mensal_28)} />
        <Card titulo="Gap até a meta (12 meses)" valor={formatarReais(r.gap_12m_meta)} />
        <Card titulo="Reforço mensal até a meta" valor={formatarReais(r.reforco_mensal_meta)} />
        <Card
          titulo="Alíquota efetiva Anexo III"
          valor={formatarPercentual(r.aliquota_efetiva_iii)}
          testid="aliquota-iii"
        />
        <Card
          titulo="Alíquota efetiva Anexo V"
          valor={formatarPercentual(r.aliquota_efetiva_v)}
          testid="aliquota-v"
        />
        <Card
          titulo="Economia estimada de DAS (III vs V, 12 meses)"
          valor={formatarReais(r.economia_12m)}
          testid="economia"
        />
      </div>
    </div>
  );
}
