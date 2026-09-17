"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { StatusDocumentoBadge } from "@/components/inbox/StatusDocumentoBadge";
import { Carregando, Erro } from "@/components/ui/Estado";
import { ApiError } from "@/lib/api";
import { listarEmpresas } from "@/lib/api/companies";
import {
  obterDocumento,
  rejeitarDocumento,
  urlArquivoOriginal,
  vincularDocumento,
} from "@/lib/api/inbox";
import { formatarPercentual, formatarReais } from "@/lib/format";

const CAMPOS: [string, string, "texto" | "reais" | "percentual"][] = [
  ["cnpj", "CNPJ", "texto"],
  ["pa", "PA", "texto"],
  ["rpa", "RPA (receita do PA)", "reais"],
  ["rbt12", "RBT12", "reais"],
  ["fs12", "FS12", "reais"],
  ["fator_r", "Fator r", "percentual"],
  ["das", "Valor do DAS", "reais"],
  ["anexo", "Anexo", "texto"],
];

export default function DocumentoPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const documento = useQuery({ queryKey: ["documento", id], queryFn: () => obterDocumento(id) });
  const empresas = useQuery({
    queryKey: ["empresas", { ativo: true }],
    queryFn: () => listarEmpresas({ ativo: true }),
  });
  const [empresaId, setEmpresaId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  if (documento.isPending) return <Carregando />;
  if (documento.isError) return <Erro texto="Documento não encontrado." />;
  const d = documento.data;
  const confiancas = (d.campos._confianca_campos ?? {}) as Record<string, string>;
  const podeDecidir = d.status === "needs_review" || d.status === "parsed";

  async function executar(acao: () => Promise<{ texto_agente?: string | null }>) {
    setErro(null);
    setMensagem(null);
    try {
      const resultado = await acao();
      setMensagem(resultado.texto_agente ?? "Feito.");
      await queryClient.invalidateQueries({ queryKey: ["documento", id] });
      await queryClient.invalidateQueries({ queryKey: ["inbox"] });
    } catch (error) {
      setErro(
        error instanceof ApiError && error.status === 409
          ? "Esse documento não pode mais ser alterado."
          : "Não foi possível concluir a ação.",
      );
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            Extrato PGDAS-D <StatusDocumentoBadge status={d.status} />
          </h1>
          <p className="text-sm text-zinc-600">
            {d.nome_original ?? "arquivo"} · confiança {formatarPercentual(d.confianca)} · parser{" "}
            {d.parser_version ?? "—"}
          </p>
          {d.motivo && (
            <p className="text-sm text-amber-800" data-testid="motivo">
              Motivo: {d.motivo}
            </p>
          )}
          {d.company_id && (
            <p className="text-sm">
              Vinculado a{" "}
              <Link href={`/empresas/${d.company_id}`} className="underline">
                {empresas.data?.items.find((e) => e.id === d.company_id)?.nome ?? "empresa"}
              </Link>
            </p>
          )}
        </div>
        <div className="flex gap-2 text-sm">
          <a href={urlArquivoOriginal(d.id)} className="rounded border px-3 py-1.5">
            Baixar original
          </a>
          <Link
            href={`/observabilidade/traces/${d.trace_id}`}
            className="rounded border px-3 py-1.5"
          >
            Ver trace
          </Link>
        </div>
      </div>

      <table className="w-full max-w-2xl text-left text-sm" data-testid="campos-extraidos">
        <thead className="border-b text-xs text-zinc-500 uppercase">
          <tr>
            <th className="py-2">Campo</th>
            <th>Valor extraído</th>
            <th className="text-right">Confiança do campo</th>
          </tr>
        </thead>
        <tbody>
          {CAMPOS.map(([chave, rotulo, tipo]) => {
            const valor = (d.campos[chave] as string | null | undefined) ?? null;
            const exibido =
              valor === null
                ? "não encontrado"
                : tipo === "reais"
                  ? formatarReais(valor)
                  : tipo === "percentual"
                    ? formatarPercentual(valor)
                    : valor;
            return (
              <tr key={chave} className="border-b last:border-0" data-campo={chave}>
                <td className="py-1">{rotulo}</td>
                <td className={valor === null ? "text-zinc-400" : ""}>{exibido}</td>
                <td className="text-right">
                  {confiancas[chave] !== undefined ? formatarPercentual(confiancas[chave]) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {mensagem && (
        <p className="text-sm text-emerald-800" data-testid="mensagem-agente">
          {mensagem}
        </p>
      )}
      {erro && (
        <p role="alert" className="text-sm text-red-700">
          {erro}
        </p>
      )}

      {podeDecidir && (
        <div className="grid max-w-3xl gap-4 md:grid-cols-2">
          <div className="space-y-2 rounded border border-zinc-200 p-3 text-sm">
            <h2 className="font-semibold">Vincular a uma empresa</h2>
            <p className="text-xs text-zinc-500">
              Se houver receita do PA, ela é lançada só se a competência ainda não existir. A folha
              nunca é alterada.
            </p>
            <select
              name="empresa"
              value={empresaId}
              onChange={(e) => setEmpresaId(e.target.value)}
              className="block w-full rounded border border-zinc-300 px-2 py-1"
            >
              <option value="">Selecione</option>
              {empresas.data?.items.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome} · {e.cnpj_formatado}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!empresaId}
              onClick={() => executar(() => vincularDocumento(d.id, empresaId))}
              className="rounded bg-zinc-900 px-3 py-1.5 text-white disabled:opacity-50"
            >
              Vincular
            </button>
          </div>
          <div className="space-y-2 rounded border border-zinc-200 p-3 text-sm">
            <h2 className="font-semibold">Rejeitar</h2>
            <input
              name="motivo"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Motivo"
              className="block w-full rounded border border-zinc-300 px-2 py-1"
            />
            <button
              type="button"
              disabled={motivo.trim().length < 3}
              onClick={() => executar(() => rejeitarDocumento(d.id, motivo.trim()))}
              className="rounded border border-red-300 px-3 py-1.5 text-red-800 disabled:opacity-50"
            >
              Rejeitar
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
