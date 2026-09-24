"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { StatusTraceBadge } from "@/components/observabilidade/StatusTraceBadge";
import { Badge } from "@/components/ui/Badge";
import { Botao, classesBotao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { CabecalhoTabela, Tabela } from "@/components/ui/Tabela";
import { TituloPagina } from "@/components/ui/TituloPagina";
import { ApiError } from "@/lib/api";
import { avaliarTrace, obterTrace } from "@/lib/api/observability";
import type { NotaHumanaIn } from "@/lib/api/types";
import { formatarPercentual } from "@/lib/format";

function Json({ titulo, valor }: { titulo: string; valor: unknown }) {
  return (
    <details className="border-line bg-panel rounded-[10px] border p-2 text-sm" open>
      <summary className="cursor-pointer font-medium">{titulo}</summary>
      <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(valor, null, 2)}</pre>
    </details>
  );
}

function FormNota({ traceId }: { traceId: string }) {
  const queryClient = useQueryClient();
  const [nota, setNota] = useState<NotaHumanaIn["nota"]>("acerto");
  const [comentario, setComentario] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErro(null);
    setSalvo(false);
    if (nota === "erro" && comentario.trim() === "") {
      setErro("Comentário é obrigatório quando a nota é 'erro'.");
      return;
    }
    try {
      await avaliarTrace(traceId, { nota, comentario: comentario.trim() || null });
      setSalvo(true);
      setComentario("");
      await queryClient.invalidateQueries({ queryKey: ["trace", traceId] });
      await queryClient.invalidateQueries({ queryKey: ["obs-resumo"] });
      await queryClient.invalidateQueries({ queryKey: ["traces"] });
    } catch (error) {
      setErro(
        error instanceof ApiError && error.status === 422
          ? "Comentário é obrigatório quando a nota é 'erro'."
          : "Não foi possível salvar a nota.",
      );
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="border-line bg-panel space-y-2 rounded-[10px] border p-3 text-sm"
    >
      <h3 className="font-display tracking-wide uppercase">Nota humana</h3>
      <div className="flex gap-4">
        {(["acerto", "parcial", "erro"] as const).map((n) => (
          <label key={n} className="flex items-center gap-1">
            <input
              type="radio"
              name="nota"
              value={n}
              checked={nota === n}
              onChange={() => setNota(n)}
            />
            {n}
          </label>
        ))}
      </div>
      <label className="block">
        Comentário {nota === "erro" && <span className="text-danger-soft">(obrigatório)</span>}
        <textarea
          name="comentario"
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          className={`mt-1 block w-full px-2 py-1 ${classesCampo}`}
        />
      </label>
      {erro && (
        <p role="alert" className="text-danger-soft">
          {erro}
        </p>
      )}
      {salvo && <p className="text-ok">Nota registrada.</p>}
      <Botao type="submit">Registrar nota</Botao>
    </form>
  );
}

export default function TraceDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const detalhe = useQuery({
    queryKey: ["trace", id],
    queryFn: () => obterTrace(id),
    // O Langfuse ingere os spans de forma assíncrona: recarrega enquanto ainda não chegaram.
    refetchInterval: (query) => {
      const dados = query.state.data;
      return dados && !dados.spans_indisponiveis && dados.spans.length === 0 ? 5000 : false;
    },
  });

  if (detalhe.isPending) return <Carregando />;
  if (detalhe.isError) return <Erro texto="Trace não encontrado." />;
  const d = detalhe.data;
  const inicioTrace = d.spans[0]?.inicio ? new Date(d.spans[0].inicio).getTime() : 0;

  return (
    <section className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <TituloPagina>
            Trace {d.trace.agente} <StatusTraceBadge status={d.trace.status} />
          </TituloPagina>
          <p className="text-muted mt-2 font-mono text-xs" data-testid="trace-id">
            {d.trace.id}
          </p>
          <p className="text-muted text-sm">
            Gatilho: {d.trace.gatilho} · Confiança: {formatarPercentual(d.trace.confianca)} ·
            Latência: {d.trace.latencia_ms ?? "—"} ms · Langfuse: {d.trace.langfuse_sync}
          </p>
        </div>
        <a
          href={d.langfuse_url}
          target="_blank"
          rel="noreferrer"
          className={classesBotao("fantasma")}
          data-testid="abrir-langfuse"
        >
          Abrir no Langfuse
        </a>
      </div>

      <div>
        <h2 className="font-display mb-2 text-lg tracking-wide uppercase">Spans</h2>
        {d.spans_indisponiveis ? (
          <Vazio>
            Spans indisponíveis: o Langfuse não respondeu. O resumo local continua valendo.
          </Vazio>
        ) : d.spans.length === 0 ? (
          <Vazio>Os spans ainda estão sendo processados pelo Langfuse.</Vazio>
        ) : (
          <Tabela data-testid="timeline-spans">
            <CabecalhoTabela>
              <tr>
                <th className="py-2">Span</th>
                <th>Tipo</th>
                <th className="text-right">Início (+ms)</th>
                <th className="text-right">Duração</th>
                <th>Nível</th>
                <th>Modelo</th>
              </tr>
            </CabecalhoTabela>
            <tbody>
              {d.spans.map((s) => (
                <tr key={s.id} className="border-b last:border-0" data-span={s.nome}>
                  <td className={`py-1 ${s.parent_id ? "pl-4" : "font-medium"}`}>{s.nome}</td>
                  <td>{s.tipo}</td>
                  <td className="text-right">
                    {s.inicio ? new Date(s.inicio).getTime() - inicioTrace : "—"}
                  </td>
                  <td className="text-right">
                    {s.latencia_ms !== null ? `${Math.round(s.latencia_ms)} ms` : "—"}
                  </td>
                  <td>{s.nivel ?? "—"}</td>
                  <td>{s.modelo ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Json titulo="Entrada" valor={d.entrada} />
        <Json titulo="Saída" valor={d.saida} />
        <Json titulo="Decisão" valor={d.decisao} />
      </div>

      <div>
        <h2 className="font-display mb-2 text-lg tracking-wide uppercase">Nota ouro</h2>
        {d.evals_ouro.length === 0 ? (
          <Vazio>Sem avaliação ouro para este trace.</Vazio>
        ) : (
          <Tabela data-testid="evals-ouro">
            <CabecalhoTabela>
              <tr>
                <th className="py-2">Campo</th>
                <th>Esperado</th>
                <th>Obtido</th>
                <th>Resultado</th>
              </tr>
            </CabecalhoTabela>
            <tbody>
              {d.evals_ouro.map((e) => (
                <tr key={e.campo} className="border-b last:border-0">
                  <td className="py-1">{e.campo}</td>
                  <td>{e.esperado ?? "—"}</td>
                  <td>{e.obtido ?? "—"}</td>
                  <td>
                    <Badge
                      cor={e.status === "ok" ? "verde" : e.status === "erro" ? "vermelho" : "cinza"}
                    >
                      {e.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </Tabela>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <FormNota traceId={d.trace.id} />
        <div className="space-y-2 text-sm" data-testid="evals-humanas">
          <h3 className="font-display tracking-wide uppercase">Notas registradas</h3>
          {d.evals_humanas.length === 0 && <Vazio>Nenhuma nota ainda.</Vazio>}
          {d.evals_humanas.map((h) => (
            <div key={h.id} className="border-line bg-panel rounded-[10px] border p-2">
              <Badge
                cor={h.nota === "acerto" ? "verde" : h.nota === "erro" ? "vermelho" : "amarelo"}
              >
                {h.nota}
              </Badge>{" "}
              <span className="text-muted text-xs">
                {new Date(h.criado_em).toLocaleString("pt-BR")}
              </span>
              {h.comentario && <p className="mt-1">{h.comentario}</p>}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
