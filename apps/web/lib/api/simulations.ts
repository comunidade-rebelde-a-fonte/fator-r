import { apiFetch } from "@/lib/api";
import type { SimulacaoIn, SimulacaoOut } from "./types";

export const simular = (companyId: string, dados: SimulacaoIn) =>
  apiFetch<SimulacaoOut>(`/companies/${companyId}/simulations`, {
    method: "POST",
    body: JSON.stringify(dados),
  });

export const historicoSimulacoes = (companyId: string) =>
  apiFetch<SimulacaoOut[]>(`/companies/${companyId}/simulations?limit=5`);
