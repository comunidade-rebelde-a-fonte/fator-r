"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PacoteBadge } from "@/components/empresas/Badges";
import { Badge } from "@/components/ui/Badge";
import { Carregando, Erro, Vazio } from "@/components/ui/Estado";
import { listarEmpresas } from "@/lib/api/companies";
import { formatarReais } from "@/lib/format";

type Opcao = "todas" | "sim" | "nao";
const paraFiltro = (o: Opcao) => (o === "todas" ? undefined : o === "sim");

export default function EmpresasPage() {
  const [busca, setBusca] = useState("");
  const [ativo, setAtivo] = useState<Opcao>("sim");
  const [sujeita, setSujeita] = useState<Opcao>("todas");
  const filtro = { busca, ativo: paraFiltro(ativo), sujeita_fator_r: paraFiltro(sujeita) };
  const empresas = useQuery({
    queryKey: ["empresas", filtro],
    queryFn: () => listarEmpresas(filtro),
  });

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Empresas</h1>
        <Link href="/empresas/nova" className="rounded bg-zinc-900 px-3 py-1.5 text-sm text-white">
          Nova empresa
        </Link>
      </div>

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label>
          Buscar
          <input
            aria-label="Buscar por nome ou CNPJ"
            placeholder="Nome ou CNPJ"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="mt-1 block rounded border border-zinc-300 px-2 py-1"
          />
        </label>
        <label>
          Situação
          <select
            value={ativo}
            onChange={(e) => setAtivo(e.target.value as Opcao)}
            className="mt-1 block rounded border border-zinc-300 px-2 py-1"
          >
            <option value="sim">Ativas</option>
            <option value="nao">Inativas</option>
            <option value="todas">Todas</option>
          </select>
        </label>
        <label>
          Sujeita a Fator R
          <select
            value={sujeita}
            onChange={(e) => setSujeita(e.target.value as Opcao)}
            className="mt-1 block rounded border border-zinc-300 px-2 py-1"
          >
            <option value="todas">Todas</option>
            <option value="sim">Sim</option>
            <option value="nao">Não</option>
          </select>
        </label>
      </div>

      {empresas.isPending && <Carregando />}
      {empresas.isError && (
        <Erro texto="Não foi possível carregar as empresas." onRetry={() => empresas.refetch()} />
      )}
      {empresas.isSuccess && empresas.data.items.length === 0 && (
        <Vazio>Nenhuma empresa encontrada com esses filtros.</Vazio>
      )}
      {empresas.isSuccess && empresas.data.items.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead className="border-b text-xs text-zinc-500 uppercase">
            <tr>
              <th className="py-2">Empresa</th>
              <th>CNPJ</th>
              <th>Fator R</th>
              <th>Pacote</th>
              <th className="text-right">Honorário</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {empresas.data.items.map((e) => (
              <tr key={e.id} className="border-b last:border-0">
                <td className="py-2">
                  <Link href={`/empresas/${e.id}`} className="font-medium hover:underline">
                    {e.nome}
                  </Link>
                </td>
                <td className="font-mono text-xs">{e.cnpj_formatado}</td>
                <td>
                  {e.sujeita_fator_r ? <Badge cor="azul">sujeita</Badge> : <Badge>não</Badge>}
                </td>
                <td>
                  <PacoteBadge pacote={e.pacote} />
                </td>
                <td className="text-right">{formatarReais(e.honorario_mensal)}</td>
                <td>{e.ativo ? <Badge cor="verde">ativa</Badge> : <Badge>inativa</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
