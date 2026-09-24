import { API_URL, ApiError, apiFetch } from "@/lib/api";
import type { CadastroPeloExtratoOut, CompanyIn, DocumentoList, DocumentoOut } from "./types";

export const listarDocumentos = (status?: string) =>
  apiFetch<DocumentoList>(`/inbox?limit=200${status ? `&status=${status}` : ""}`);

export const obterDocumento = (id: string) => apiFetch<DocumentoOut>(`/inbox/${id}`);

export const urlArquivoOriginal = (id: string) => `${API_URL}/inbox/${id}/arquivo`;

/** Upload multipart (sem Content-Type JSON; o navegador define o boundary). */
export async function enviarExtrato(arquivo: File): Promise<DocumentoOut> {
  const corpo = new FormData();
  corpo.append("arquivo", arquivo);
  const response = await fetch(`${API_URL}/inbox/pgdas`, {
    method: "POST",
    body: corpo,
    credentials: "include",
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.json().catch(() => null));
  }
  return (await response.json()) as DocumentoOut;
}

export const vincularDocumento = (id: string, companyId: string) =>
  apiFetch<DocumentoOut>(`/inbox/${id}/link`, {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  });

export const rejeitarDocumento = (id: string, motivo: string) =>
  apiFetch<DocumentoOut>(`/inbox/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ motivo }),
  });

/** Cadastra a empresa do extrato e vincula o documento numa chamada só (M8). */
export const cadastrarEmpresaPeloExtrato = (id: string, dados: CompanyIn) =>
  apiFetch<CadastroPeloExtratoOut>(`/inbox/${id}/cadastrar-empresa`, {
    method: "POST",
    body: JSON.stringify(dados),
  });
