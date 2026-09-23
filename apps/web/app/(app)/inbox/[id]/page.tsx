"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { CadastroPeloExtrato } from "@/components/inbox/CadastroPeloExtrato";
import { StatusDocumentoBadge } from "@/components/inbox/StatusDocumentoBadge";
import { Botao, classesBotao } from "@/components/ui/Botao";
import { classesCampo } from "@/components/ui/Campo";
import { Carregando, Erro } from "@/components/ui/Estado";
import { Painel } from "@/components/ui/Painel";
import { CabecalhoTabela, Tabela } from "@/components/ui/Tabela";
import { TituloPagina } from "@/components/ui/TituloPagina";
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
  const identificacao = (d.campos._identificacao ?? {}) as { nome_empresarial?: string | null };
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
          <TituloPagina>
            Extrato PGDAS-D <StatusDocumentoBadge status={d.status} />
          </TituloPagina>
          <p className="text-muted mt-2 text-sm">
            {d.nome_original ?? "arquivo"} · confiança {formatarPercentual(d.confianca)} · parser{" "}
            {d.parser_version ?? "—"}
          </p>
          {identificacao.nome_empresarial && (
            <p className="text-sm" data-testid="nome-empresarial">
              Nome empresarial no extrato: {identificacao.nome_empresarial}
            </p>
          )}
          {d.motivo && (
            <p className="text-accent-soft text-sm" data-testid="motivo">
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
          <a href={urlArquivoOriginal(d.id)} className={classesBotao("fantasma")}>
            Baixar original
          </a>
          <Link href={`/observabilidade/traces/${d.trace_id}`} className={classesBotao("fantasma")}>
            Ver trace
          </Link>
        </div>
      </div>

      <Tabela className="max-w-2xl" data-testid="campos-extraidos">
        <CabecalhoTabela>
          <tr>
            <th className="py-2">Campo</th>
            <th>Valor extraído</th>
            <th className="text-right">Confiança do campo</th>
          </tr>
        </CabecalhoTabela>
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
                <td className={valor === null ? "text-muted" : ""}>{exibido}</td>
                <td className="text-right">
                  {confiancas[chave] !== undefined ? formatarPercentual(confiancas[chave]) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </Tabela>

      {mensagem && (
        <p className="text-ok text-sm" data-testid="mensagem-agente">
          {mensagem}
        </p>
      )}
      {erro && (
        <p role="alert" className="text-danger-soft text-sm">
          {erro}
        </p>
      )}

      <CadastroPeloExtrato
        documento={d}
        onConcluido={(atualizado) => setMensagem(atualizado.texto_agente ?? "Feito.")}
      />

      {podeDecidir && (
        <div className="grid max-w-3xl gap-4 md:grid-cols-2">
          <Painel className="space-y-2 p-3 text-sm">
            <h2 className="font-display tracking-wide uppercase">Vincular a uma empresa</h2>
            <p className="text-muted text-xs">
              Se houver receita do PA, ela é lançada só se a competência ainda não existir. A folha
              nunca é alterada.
            </p>
            <select
              name="empresa"
              value={empresaId}
              onChange={(e) => setEmpresaId(e.target.value)}
              className={`block w-full px-2 py-1 ${classesCampo}`}
            >
              <option value="">Selecione</option>
              {empresas.data?.items.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome} · {e.cnpj_formatado}
                </option>
              ))}
            </select>
            <Botao
              disabled={!empresaId}
              onClick={() => executar(() => vincularDocumento(d.id, empresaId))}
            >
              Vincular
            </Botao>
          </Painel>
          <Painel className="space-y-2 p-3 text-sm">
            <h2 className="font-display tracking-wide uppercase">Rejeitar</h2>
            <input
              name="motivo"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Motivo"
              className={`block w-full px-2 py-1 ${classesCampo}`}
            />
            <Botao
              variante="perigo"
              disabled={motivo.trim().length < 3}
              onClick={() => executar(() => rejeitarDocumento(d.id, motivo.trim()))}
            >
              Rejeitar
            </Botao>
          </Painel>
        </div>
      )}
    </section>
  );
}
