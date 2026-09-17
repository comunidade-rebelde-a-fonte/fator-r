"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppNav } from "@/components/AppNav";
import { ApiError } from "@/lib/api";
import { logout, useMe } from "@/lib/auth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useMe();
  const semSessao = me.error instanceof ApiError && me.error.status === 401;

  useEffect(() => {
    if (semSessao) router.replace("/login");
  }, [semSessao, router]);

  async function sair() {
    try {
      await logout();
    } finally {
      queryClient.clear();
      router.replace("/login");
    }
  }

  if (me.isPending || semSessao) {
    return (
      <p role="status" className="p-6 text-sm text-zinc-500">
        Carregando...
      </p>
    );
  }

  if (me.isError) {
    return (
      <div role="alert" className="p-6 text-sm text-red-700">
        Não foi possível falar com a API.{" "}
        <button type="button" className="underline" onClick={() => me.refetch()}>
          Tentar de novo
        </button>
      </div>
    );
  }

  return (
    <>
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3">
        <div className="flex items-center gap-6">
          <span className="font-semibold">Fator R</span>
          <AppNav />
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-zinc-600">{me.data.nome}</span>
          <button type="button" onClick={sair} className="rounded border px-2 py-1">
            Sair
          </button>
        </div>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </>
  );
}
