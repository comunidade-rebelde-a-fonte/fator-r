import { apiFetch } from "@/lib/api";
import type { RespostaAgente } from "./types";

export const perguntarConsultor = (mensagem: string, companyId?: string) =>
  apiFetch<RespostaAgente>("/agents/consultor/chat", {
    method: "POST",
    body: JSON.stringify({ mensagem, company_id: companyId ?? null }),
  });

export const perguntarPriorizador = (mensagem: string, pa?: string) =>
  apiFetch<RespostaAgente>("/agents/priorizador/chat", {
    method: "POST",
    body: JSON.stringify({ mensagem, pa: pa || null }),
  });
