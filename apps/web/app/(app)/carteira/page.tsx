"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PacoteBadge } from "@/components/empresas/Badges";
import { SemaforoBadge } from "@/components/fator-r/SemaforoBadge";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { obterCarteira } from "@/lib/api/portfolio";
import type { CarteiraOut } from "@/lib/api/types";
import {
  competenciaAtual,
  formatarPercentual,
  formatarReais,
  rotuloCompetencia,
} from "@/lib/format";

function Kpi({ titulo, valor, testid }: { titulo: string; valor: string; testid: string }) {
  return (
    <div className="rounded border border-zinc-200 p-3">
      <div className="text-xs text-zinc-500">{titulo}</div>
      <div className="mt-1 text-xl font-semibold" data-testid={testid}>
        {valor}
      </div>
    </div>
  );
}

function Kpis({ kpis }: { kpis: CarteiraOut["kpis"] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
      <Kpi titulo="Monitoradas" valor={String(kpis.monitoradas)} testid="kpi-monitoradas" />
      <Kpi titulo="No Anexo V" valor={String(kpis.no_v)} testid="kpi-no-v" />
      <Kpi titulo="No limite (28–30%)" valor={String(kpis.no_limite)} testid="kpi-no-limite" />
      <Kpi titulo="Seguras" valor={String(kpis.seguras)} testid="kpi-seguras" />
      <Kpi
        titulo="Economia em jogo (12 meses)"
        valor={formatarReais(kpis.economia_em_jogo)}
        testid="kpi-economia"
      />
      <Kpi
        titulo="Receita dos pacotes (mês)"
        valor={formatarReais(kpis.honorarios_pacotes)}
        testid="kpi-honorarios"
      />
    </div>
  );
}

export default function CarteiraPage() {
  const [pa, setPa] = useState(competenciaAtual());
  const carteira = useQuery({ queryKey: ["carteira", pa], queryFn: () => obterCarteira(pa) });

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Carteira</h1>
        <label className="flex items-center gap-2 text-sm">
          Período de apuração (PA)
          <input
            type="month"
            name="pa"
            value={pa}
            onChange={(e) => e.target.value && setPa(e.target.value)}
            className="rounded border border-zinc-300 px-2 py-1"
          />
        </label>
      </div>

      {carteira.isPending && <Carregando />}
      {carteira.isError && (
        <Erro texto="Não foi possível carregar a carteira." onRetry={() => carteira.refetch()} />
      )}
      {carteira.isSuccess && (
        <>
          <Kpis kpis={carteira.data.kpis} />
          {carteira.data.linhas.length === 0 ? (
            <Vazio>
              Nenhuma empresa ativa sujeita a Fator R. Cadastre empresas e marque &quot;sujeita a
              Fator R&quot;.
            </Vazio>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm" data-testid="tabela-carteira">
                <thead className="border-b text-xs text-zinc-500 uppercase">
                  <tr>
                    <th className="py-2">Ação sugerida</th>
                    <th>Empresa</th>
                    <th>Semáforo</th>
                    <th className="text-right">Fator R</th>
                    <th>Anexo</th>
                    <th className="text-right">RBT12</th>
                    <th className="text-right">FS12</th>
                    <th className="text-right">Reforço mensal (28% · meta)</th>
                    <th className="text-right">Economia 12 meses</th>
                  </tr>
                </thead>
                <tbody>
                  {carteira.data.linhas.map((l) => (
                    <tr
                      key={l.company_id}
                      className="border-b last:border-0"
                      data-semaforo={l.semaforo ?? "insuficiente"}
                    >
                      <td className="py-2 font-medium">{l.acao_texto}</td>
                      <td>
                        <Link href={`/empresas/${l.company_id}`} className="hover:underline">
                          {l.nome}
                        </Link>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <span className="font-mono">{l.cnpj_formatado}</span>
                          <PacoteBadge pacote={l.pacote} />
                        </div>
                        {l.meses_faltantes.length > 0 && (
                          <div className="text-xs text-red-700">
                            Faltam: {l.meses_faltantes.map(rotuloCompetencia).join(", ")}
                          </div>
                        )}
                      </td>
                      <td>
                        <SemaforoBadge semaforo={l.semaforo} />
                      </td>
                      <td className="text-right">{formatarPercentual(l.fator_r)}</td>
                      <td>{l.anexo ?? "—"}</td>
                      <td className="text-right">{formatarReais(l.rbt12)}</td>
                      <td className="text-right">{formatarReais(l.fs12)}</td>
                      <td className="text-right whitespace-nowrap">
                        {formatarReais(l.reforco_mensal_28)} ·{" "}
                        {formatarReais(l.reforco_mensal_meta)}
                      </td>
                      <td className="text-right">{formatarReais(l.economia_12m)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
