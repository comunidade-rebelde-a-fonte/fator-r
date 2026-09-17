import { apiFetch } from "@/lib/api";
import type { CarteiraOut } from "./types";

export const obterCarteira = (pa: string) => apiFetch<CarteiraOut>(`/portfolio?pa=${pa}`);
