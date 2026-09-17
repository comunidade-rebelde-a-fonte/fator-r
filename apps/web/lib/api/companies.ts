import { apiFetch } from "@/lib/api";
import type {
  CompanyIn,
  CompanyList,
  CompanyOut,
  CompanyPatch,
  FatorROut,
  MovementIn,
  MovementOut,
} from "./types";

export type FiltroEmpresas = {
  busca?: string;
  ativo?: boolean;
  sujeita_fator_r?: boolean;
};

export function listarEmpresas(filtro: FiltroEmpresas): Promise<CompanyList> {
  const params = new URLSearchParams({ limit: "500" });
  if (filtro.busca) params.set("busca", filtro.busca);
  if (filtro.ativo !== undefined) params.set("ativo", String(filtro.ativo));
  if (filtro.sujeita_fator_r !== undefined)
    params.set("sujeita_fator_r", String(filtro.sujeita_fator_r));
  return apiFetch<CompanyList>(`/companies?${params}`);
}

export const obterEmpresa = (id: string) => apiFetch<CompanyOut>(`/companies/${id}`);

export const criarEmpresa = (dados: CompanyIn) =>
  apiFetch<CompanyOut>("/companies", { method: "POST", body: JSON.stringify(dados) });

export const atualizarEmpresa = (id: string, dados: CompanyPatch) =>
  apiFetch<CompanyOut>(`/companies/${id}`, { method: "PATCH", body: JSON.stringify(dados) });

export const listarMovimentos = (id: string, de: string, ate: string) =>
  apiFetch<MovementOut[]>(`/companies/${id}/movements?de=${de}&ate=${ate}`);

export const lancarMovimento = (id: string, competencia: string, dados: MovementIn) =>
  apiFetch<MovementOut>(`/companies/${id}/movements/${competencia}`, {
    method: "PUT",
    body: JSON.stringify(dados),
  });

export const obterFatorR = (id: string, pa: string) =>
  apiFetch<FatorROut>(`/companies/${id}/fator-r?pa=${pa}`);
