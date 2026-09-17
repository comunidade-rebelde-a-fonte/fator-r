import { apiFetch } from "@/lib/api";
import type { NotaHumanaIn, ResumoOut, TraceDetalheOut, TraceList } from "./types";

export type FiltroTraces = { agente?: string; status?: string; sem_nota?: boolean };

export const obterResumo = () => apiFetch<ResumoOut>("/observability/summary");

export function listarTraces(filtro: FiltroTraces): Promise<TraceList> {
  const params = new URLSearchParams({ limit: "100" });
  if (filtro.agente) params.set("agente", filtro.agente);
  if (filtro.status) params.set("status", filtro.status);
  if (filtro.sem_nota) params.set("sem_nota", "true");
  return apiFetch<TraceList>(`/traces?${params}`);
}

export const obterTrace = (id: string) => apiFetch<TraceDetalheOut>(`/traces/${id}`);

export const avaliarTrace = (id: string, nota: NotaHumanaIn) =>
  apiFetch(`/traces/${id}/human-eval`, { method: "POST", body: JSON.stringify(nota) });
