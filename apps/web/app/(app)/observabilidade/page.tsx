"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { StatusTraceBadge } from "@/components/observabilidade/StatusTraceBadge";
import { Badge } from "@/components/ui/Badge";
import { classesCampo } from "@/components/ui/Campo";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { Painel } from "@/components/ui/Painel";
import { CabecalhoTabela, Tabela } from "@/components/ui/Tabela";
import { TituloPagina } from "@/components/ui/TituloPagina";
import { listarTraces, obterResumo } from "@/lib/api/observability";
import { formatarPercentual } from "@/lib/format";

function Card({ titulo, valor, testid }: { titulo: string; valor: string; testid: string }) {
  return (
    <Painel className="p-3">
      <div className="text-muted text-[11px] tracking-[.1em] uppercase">{titulo}</div>
      <div className="font-display mt-1 text-2xl" data-testid={testid}>
        {valor}
      </div>
    </Painel>
  );
}

const dolar = (v: string | null | undefined) =>
  v === null || v === undefined ? "—" : `US$ ${Number(v).toFixed(4)}`;

export default function ObservabilidadePage() {
  const [agente, setAgente] = useState("");
  const [status, setStatus] = useState("");
  const [semNota, setSemNota] = useState(false);
  const resumo = useQuery({ queryKey: ["obs-resumo"], queryFn: obterResumo });
  const filtro = { agente, status, sem_nota: semNota };
  const traces = useQuery({ queryKey: ["traces", filtro], queryFn: () => listarTraces(filtro) });

  return (
    <section className="space-y-6">
      <TituloPagina>Observabilidade dos agentes</TituloPagina>

      {resumo.isPending && <Carregando />}
      {resumo.isError && (
        <Erro texto="Não foi possível carregar o painel." onRetry={() => resumo.refetch()} />
      )}
      {resumo.isSuccess && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <Card titulo="Corridas 24h" valor={String(resumo.data.corridas_24h)} testid="obs-24h" />
            <Card
              titulo="Corridas (total)"
              valor={String(resumo.data.corridas_total)}
              testid="obs-total"
            />
            <Card
              titulo="Pendências sem nota humana"
              valor={String(resumo.data.pendencias_sem_nota)}
              testid="obs-pendencias"
            />
            <Card
              titulo="Acerto ouro"
              valor={formatarPercentual(resumo.data.acerto_ouro)}
              testid="obs-acerto-ouro"
            />
            <Card
              titulo="Acerto humano"
              valor={formatarPercentual(resumo.data.acerto_humano)}
              testid="obs-acerto-humano"
            />
            <Card
              titulo="Custo do Claude (30 dias)"
              valor={dolar(resumo.data.custo_llm_30d)}
              testid="obs-custo"
            />
          </div>

          <div>
            <h2 className="font-display mb-2 text-lg tracking-wide uppercase">Por agente</h2>
            {resumo.data.por_agente.length === 0 ? (
              <Vazio>Nenhuma corrida de agente ainda.</Vazio>
            ) : (
              <Tabela data-testid="tabela-agentes">
                <CabecalhoTabela>
                  <tr>
                    <th className="py-2">Agente</th>
                    <th className="text-right">Volume</th>
                    <th className="text-right">Latência média</th>
                    <th className="text-right">Confiança média</th>
                    <th className="text-right">Erros</th>
                    <th className="text-right">Reviews</th>
                  </tr>
                </CabecalhoTabela>
                <tbody>
                  {resumo.data.por_agente.map((a) => (
                    <tr key={a.agente} className="border-b last:border-0">
                      <td className="py-2 font-medium">{a.agente}</td>
                      <td className="text-right">{a.volume}</td>
                      <td className="text-right">
                        {a.latencia_media_ms
                          ? `${Math.round(Number(a.latencia_media_ms))} ms`
                          : "—"}
                      </td>
                      <td className="text-right">{formatarPercentual(a.confianca_media)}</td>
                      <td className="text-right">{a.erros}</td>
                      <td className="text-right">{a.reviews}</td>
                    </tr>
                  ))}
                </tbody>
              </Tabela>
            )}
          </div>
        </>
      )}

      <div className="space-y-2">
        <h2 className="font-display text-lg tracking-wide uppercase">Traces</h2>
        <div className="flex flex-wrap items-end gap-3 text-sm">
          <label className="text-muted">
            Agente
            <select
              name="agente"
              value={agente}
              onChange={(e) => setAgente(e.target.value)}
              className={`mt-1 block px-2 py-1 ${classesCampo}`}
            >
              <option value="">Todos</option>
              {resumo.data?.por_agente.map((a) => (
                <option key={a.agente} value={a.agente}>
                  {a.agente}
                </option>
              ))}
            </select>
          </label>
          <label className="text-muted">
            Status
            <select
              name="status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className={`mt-1 block px-2 py-1 ${classesCampo}`}
            >
              <option value="">Todos</option>
              <option value="ok">ok</option>
              <option value="needs_review">revisão</option>
              <option value="error">erro</option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              name="sem_nota"
              checked={semNota}
              onChange={(e) => setSemNota(e.target.checked)}
            />
            Só sem nota humana
          </label>
        </div>
        {traces.isPending && <Carregando />}
        {traces.isError && (
          <Erro texto="Não foi possível carregar os traces." onRetry={() => traces.refetch()} />
        )}
        {traces.isSuccess && traces.data.items.length === 0 && (
          <Vazio>Nenhum trace com esses filtros.</Vazio>
        )}
        {traces.isSuccess && traces.data.items.length > 0 && (
          <Tabela data-testid="tabela-traces">
            <CabecalhoTabela>
              <tr>
                <th className="py-2">Quando</th>
                <th>Agente</th>
                <th>Gatilho</th>
                <th>Status</th>
                <th className="text-right">Confiança</th>
                <th className="text-right">Latência</th>
                <th>Nota humana</th>
                <th>Langfuse</th>
              </tr>
            </CabecalhoTabela>
            <tbody>
              {traces.data.items.map((t) => (
                <tr key={t.id} className="border-b last:border-0" data-trace={t.id}>
                  <td className="py-2">
                    <Link href={`/observabilidade/traces/${t.id}`} className="hover:underline">
                      {new Date(t.criado_em).toLocaleString("pt-BR")}
                    </Link>
                  </td>
                  <td>{t.agente}</td>
                  <td>{t.gatilho}</td>
                  <td>
                    <StatusTraceBadge status={t.status} />
                  </td>
                  <td className="text-right">{formatarPercentual(t.confianca)}</td>
                  <td className="text-right">{t.latencia_ms ?? "—"} ms</td>
                  <td>
                    {t.tem_nota_humana ? (
                      <Badge cor="verde">avaliado</Badge>
                    ) : (
                      <Badge>pendente</Badge>
                    )}
                  </td>
                  <td>
                    <Badge
                      cor={
                        t.langfuse_sync === "failed"
                          ? "vermelho"
                          : t.langfuse_sync === "ok"
                            ? "verde"
                            : "cinza"
                      }
                    >
                      {t.langfuse_sync}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </div>
    </section>
  );
}
