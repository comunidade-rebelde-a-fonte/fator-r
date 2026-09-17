import { useQuery } from "@tanstack/react-query";

import { apiFetch, ApiError } from "./api";

export type Me = {
  id: string;
  firm_id: string;
  email: string;
  nome: string;
};

export const ME_QUERY_KEY = ["auth", "me"] as const;

export function useMe() {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => apiFetch<Me>("/auth/me"),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status === 401) && failureCount < 1,
  });
}

export function login(email: string, senha: string): Promise<Me> {
  return apiFetch<Me>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
}

export function logout(): Promise<void> {
  return apiFetch<void>("/auth/logout", { method: "POST" });
}
