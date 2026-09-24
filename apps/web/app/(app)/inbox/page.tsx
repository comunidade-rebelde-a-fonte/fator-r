"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState, type DragEvent } from "react";

import { CadastroPeloExtrato } from "@/components/inbox/CadastroPeloExtrato";
import { STATUS_DOCUMENTO, StatusDocumentoBadge } from "@/components/inbox/StatusDocumentoBadge";
import { classesBotao } from "@/components/ui/Botao";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { CabecalhoTabela, Tabela } from "@/components/ui/Tabela";
import { TituloPagina } from "@/components/ui/TituloPagina";
import { ApiError } from "@/lib/api";
import { enviarExtrato, listarDocumentos } from "@/lib/api/inbox";
import type { DocumentoOut, StatusDocumento } from "@/lib/api/types";
import { formatarPercentual } from "@/lib/format";

function classesFiltro(ativo: boolean): string {
  return `rounded-[4px] border px-2 py-1 transition-colors ${
    ativo ? "border-accent/60 bg-accent/12 text-fg" : "border-line-strong text-muted hover:text-fg"
  }`;
}

function mensagemUpload(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 415) return "Formato não aceito. Envie o extrato em PDF ou TXT.";
    if (error.status === 413) return "Arquivo acima do tamanho máximo.";
  }
  return "Não foi possível enviar o arquivo.";
}

export default function InboxPage() {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [filtro, setFiltro] = useState<StatusDocumento | "">("");
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [ultimo, setUltimo] = useState<DocumentoOut | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const documentos = useQuery({
    queryKey: ["inbox", filtro],
    queryFn: () => listarDocumentos(filtro || undefined),
  });

  async function enviar(arquivos: FileList | null) {
    if (!arquivos?.length) return;
    setErro(null);
    setEnviando(true);
    try {
      for (const arquivo of Array.from(arquivos)) {
        setUltimo(await enviarExtrato(arquivo));
      }
      await queryClient.invalidateQueries({ queryKey: ["inbox"] });
    } catch (error) {
      setErro(mensagemUpload(error));
    } finally {
      setEnviando(false);
      if (input.current) input.current.value = "";
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setArrastando(false);
    void enviar(event.dataTransfer.files);
  }

  const contagem = documentos.data?.contagem_por_status ?? {};

  return (
    <section className="space-y-4">
      <TituloPagina>Inbox PGDAS-D</TituloPagina>

      <div
        data-testid="dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setArrastando(true);
        }}
        onDragLeave={() => setArrastando(false)}
        onDrop={onDrop}
        className={`rounded-[10px] border-2 border-dashed p-6 text-center text-sm transition-colors ${
          arrastando ? "border-accent bg-accent/8" : "border-line-strong/60 bg-panel"
        }`}
      >
        <p>Arraste o extrato do PGDAS-D (PDF ou TXT) ou</p>
        <label className={classesBotao("primario", "md", "mt-2 cursor-pointer")}>
          escolha o arquivo
          <input
            ref={input}
            type="file"
            name="arquivo"
            accept=".pdf,.txt,application/pdf,text/plain"
            multiple
            className="hidden"
            onChange={(e) => void enviar(e.target.files)}
          />
        </label>
        {enviando && <p className="text-muted mt-2">Enviando e lendo o extrato...</p>}
        {erro && (
          <p role="alert" className="text-danger-soft mt-2">
            {erro}
          </p>
        )}
        {ultimo && !enviando && (
          <p className="mt-2" data-testid="resultado-upload">
            <StatusDocumentoBadge status={ultimo.status} /> {ultimo.texto_agente}{" "}
            <Link href={`/inbox/${ultimo.id}`} className="underline">
              ver documento
            </Link>
          </p>
        )}
      </div>

      {ultimo && !enviando && (
        <CadastroPeloExtrato key={ultimo.id} documento={ultimo} onConcluido={setUltimo} />
      )}

      <div className="flex flex-wrap gap-2 text-sm">
        <button
          type="button"
          onClick={() => setFiltro("")}
          className={classesFiltro(filtro === "")}
        >
          Todos
        </button>
        {(Object.keys(STATUS_DOCUMENTO) as StatusDocumento[]).map((s) => (
          <button
            key={s}
            type="button"
            data-filtro={s}
            onClick={() => setFiltro(s)}
            className={classesFiltro(filtro === s)}
          >
            {STATUS_DOCUMENTO[s].rotulo} ({contagem[s] ?? 0})
          </button>
        ))}
      </div>

      {documentos.isPending && <Carregando />}
      {documentos.isError && (
        <Erro texto="Não foi possível carregar a inbox." onRetry={() => documentos.refetch()} />
      )}
      {documentos.isSuccess && documentos.data.items.length === 0 && (
        <Vazio>Nenhum extrato nesta situação.</Vazio>
      )}
      {documentos.isSuccess && documentos.data.items.length > 0 && (
        <Tabela data-testid="tabela-inbox">
          <CabecalhoTabela>
            <tr>
              <th className="py-2">Recebido em</th>
              <th>Arquivo</th>
              <th>PA</th>
              <th>CNPJ</th>
              <th>Status</th>
              <th>Motivo</th>
              <th className="text-right">Confiança</th>
            </tr>
          </CabecalhoTabela>
          <tbody>
            {documentos.data.items.map((d) => (
              <tr key={d.id} className="border-b last:border-0" data-documento={d.id}>
                <td className="py-2">
                  <Link href={`/inbox/${d.id}`} className="hover:underline">
                    {new Date(d.criado_em).toLocaleString("pt-BR")}
                  </Link>
                </td>
                <td>{d.nome_original ?? "—"}</td>
                <td>{(d.campos.pa as string | null) ?? "—"}</td>
                <td className="font-mono text-xs">{(d.campos.cnpj as string | null) ?? "—"}</td>
                <td>
                  <StatusDocumentoBadge status={d.status} />
                </td>
                <td className="text-muted text-xs">{d.motivo ?? ""}</td>
                <td className="text-right">{formatarPercentual(d.confianca)}</td>
              </tr>
            ))}
          </tbody>
        </Tabela>
      )}
    </section>
  );
}
