"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppNav } from "@/components/AppNav";
import { Botao } from "@/components/ui/Botao";
import { ApiError } from "@/lib/api";
import { logout, useMe } from "@/lib/auth";

/** Casca do layout autenticado. A `marca` vem do server (logo opcional em `public/brand/`). */
export function AppShell({ marca, children }: { marca: ReactNode; children: ReactNode }) {
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
      <p role="status" className="text-muted p-6 text-sm">
        Carregando...
      </p>
    );
  }

  if (me.isError) {
    return (
      <div role="alert" className="text-danger-soft p-6 text-sm">
        Não foi possível falar com a API.{" "}
        <button type="button" className="underline" onClick={() => me.refetch()}>
          Tentar de novo
        </button>
      </div>
    );
  }

  return (
    <>
      <header className="bg-base flex h-16 items-center justify-between border-b px-6">
        <div className="flex h-full items-center gap-8">
          {marca}
          <AppNav />
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted">{me.data.nome}</span>
          <Botao variante="fantasma" onClick={sair}>
            Sair
          </Botao>
        </div>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </>
  );
}
