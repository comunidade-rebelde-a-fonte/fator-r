"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PacoteBadge } from "@/components/empresas/Badges";
import { SemaforoBadge } from "@/components/fator-r/SemaforoBadge";
import { classesCampo } from "@/components/ui/Campo";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { Painel } from "@/components/ui/Painel";
import { CabecalhoTabela, Tabela } from "@/components/ui/Tabela";
import { TituloPagina } from "@/components/ui/TituloPagina";
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
    <Painel className="p-3">
      <div className="text-muted text-[11px] tracking-[.1em] uppercase">{titulo}</div>
      <div className="font-display mt-1 text-2xl" data-testid={testid}>
        {valor}
      </div>
    </Painel>
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
      <TituloPagina
        acoes={
          <label className="text-muted flex items-center gap-2 text-sm">
            Período de apuração (PA)
            <input
              type="month"
              name="pa"
              value={pa}
              onChange={(e) => e.target.value && setPa(e.target.value)}
              className={`${classesCampo} px-2 py-1`}
            />
          </label>
        }
      >
        Carteira
      </TituloPagina>

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
              <Tabela data-testid="tabela-carteira">
                <CabecalhoTabela>
                  <tr>
                    <th className="py-2">Ação sugerida</th>
                    <th>Empresa</th>
                    <th>Semáforo</th>
                    <th className="text-right">Fator R</th>
                    <th>Anexo</th>
                    <th className="text-right">RBT12</th>
                    <th className="text-right">FS12</th>
                    <th className="text-right">Aumento de folha por mês</th>
                    <th className="text-right">Economia 12 meses</th>
                  </tr>
                </CabecalhoTabela>
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
                        <div className="text-muted flex items-center gap-2 text-xs">
                          <span className="font-mono">{l.cnpj_formatado}</span>
                          <PacoteBadge pacote={l.pacote} />
                        </div>
                        {l.meses_faltantes.length > 0 && (
                          <div className="text-danger-soft text-xs">
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
                      <td className="text-right" data-testid="aumento-folha">
                        <AumentoDeFolha
                          ate28={l.reforco_mensal_28}
                          ateMeta={l.reforco_mensal_meta}
                          meta={l.meta_operacional}
                        />
                      </td>
                      <td className="text-right">{formatarReais(l.economia_12m)}</td>
                    </tr>
                  ))}
                </tbody>
              </Tabela>
            </div>
          )}
        </>
      )}
    </section>
  );
}

/** Quanto a folha mensal precisa subir: valores já calculados pelo motor, aqui só rotulados. */
function AumentoDeFolha({
  ate28,
  ateMeta,
  meta,
}: {
  ate28: string | null;
  ateMeta: string | null;
  meta: string;
}) {
  if (ate28 === null || ateMeta === null) return <span className="text-muted">—</span>;
  const rotuloMeta = `meta de ${formatarPercentual(meta)}`;
  const precisa28 = Number(ate28) > 0;
  const precisaMeta = Number(ateMeta) > 0;
  if (!precisaMeta) return <span className="text-ok">já na {rotuloMeta}</span>;
  return (
    <div className="space-y-0.5 whitespace-nowrap">
      {precisa28 ? (
        <div>
          <strong>+ {formatarReais(ate28)}</strong>{" "}
          <span className="text-muted text-xs">para chegar a 28% (Anexo III)</span>
        </div>
      ) : (
        <div className="text-ok text-xs">já atinge 28% (Anexo III)</div>
      )}
      <div>
        + {formatarReais(ateMeta)} <span className="text-muted text-xs">para a {rotuloMeta}</span>
      </div>
    </div>
  );
}
