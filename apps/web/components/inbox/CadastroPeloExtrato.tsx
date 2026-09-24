"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { EmpresaForm } from "@/components/empresas/EmpresaForm";
import { Botao } from "@/components/ui/Botao";
import { ApiError } from "@/lib/api";
import { cadastrarEmpresaPeloExtrato, vincularDocumento } from "@/lib/api/inbox";
import type { DocumentoOut } from "@/lib/api/types";

/** 409 com `detail.codigo = cnpj_ja_cadastrado`: alguém cadastrou o CNPJ no meio do caminho. */
function empresaJaCadastrada(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  // ApiError.detail guarda o corpo da resposta; o FastAPI põe o erro em `corpo.detail`.
  const corpo = error.detail as { detail?: { codigo?: string; company_id?: string | null } } | null;
  const d = corpo?.detail;
  return d?.codigo === "cnpj_ja_cadastrado" ? (d.company_id ?? null) : null;
}

/**
 * CNPJ do extrato fora da carteira: cadastra a empresa e vincula o documento (M8).
 * Nada é gravado sem o analista confirmar o formulário (CLAUDE.md §3.9).
 */
export function CadastroPeloExtrato({
  documento,
  onConcluido,
}: {
  documento: DocumentoOut;
  onConcluido: (documento: DocumentoOut) => void;
}) {
  const queryClient = useQueryClient();
  const [aberto, setAberto] = useState(false);
  const [empresaExistente, setEmpresaExistente] = useState<string | null>(null);
  const [erroVinculo, setErroVinculo] = useState<string | null>(null);
  const sugestao = documento.sugestao_cadastro;
  if (!sugestao) return null;

  async function concluir(atualizado: DocumentoOut) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["inbox"] }),
      queryClient.invalidateQueries({ queryKey: ["documento", documento.id] }),
      queryClient.invalidateQueries({ queryKey: ["empresas"] }),
    ]);
    onConcluido(atualizado);
  }

  async function vincularAExistente(companyId: string) {
    setErroVinculo(null);
    try {
      await concluir(await vincularDocumento(documento.id, companyId));
    } catch {
      setErroVinculo("Não foi possível vincular. Atualize a página e tente de novo.");
    }
  }

  return (
    <div
      data-testid="cadastro-pelo-extrato"
      className="border-accent/40 bg-accent/8 space-y-3 rounded-[10px] border p-3 text-left text-sm"
    >
      <p>
        <strong>Esse CNPJ não está na sua carteira</strong> ({sugestao.cnpj_formatado}).{" "}
        {sugestao.nome_empresarial && <>O extrato indica: {sugestao.nome_empresarial}.</>}
      </p>
      {!aberto && <Botao onClick={() => setAberto(true)}>Cadastrar e vincular</Botao>}
      {aberto && (
        <EmpresaForm
          inicial={{
            nome: sugestao.nome_empresarial ?? "",
            cnpj_formatado: sugestao.cnpj_formatado,
            sujeita_fator_r: sugestao.sujeita_fator_r,
            inicio_atividade: sugestao.inicio_atividade ?? null,
          }}
          cnpjSomenteLeitura
          rotuloSalvar="Confirmar cadastro e vínculo"
          onSalvar={async (dados) => {
            setEmpresaExistente(null);
            try {
              const resultado = await cadastrarEmpresaPeloExtrato(documento.id, dados);
              await concluir(resultado.documento);
            } catch (error) {
              setEmpresaExistente(empresaJaCadastrada(error));
              throw error;
            }
          }}
        />
      )}
      {empresaExistente && (
        <button
          type="button"
          onClick={() => void vincularAExistente(empresaExistente)}
          className="underline"
        >
          Vincular à empresa já cadastrada
        </button>
      )}
      {erroVinculo && (
        <p role="alert" className="text-danger-soft">
          {erroVinculo}
        </p>
      )}
    </div>
  );
}
