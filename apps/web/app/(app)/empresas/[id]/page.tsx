"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Chat } from "@/components/agentes/Chat";
import { PacoteBadge } from "@/components/empresas/Badges";
import { PainelFatorR } from "@/components/fator-r/PainelFatorR";
import { Simulador } from "@/components/simulador/Simulador";
import { GradeMensal } from "@/components/empresas/GradeMensal";
import { Badge } from "@/components/ui/Badge";
import { Carregando, Erro } from "@/components/ui/Estado";
import { perguntarConsultor } from "@/lib/api/agents";
import { atualizarEmpresa, obterEmpresa } from "@/lib/api/companies";
import { formatarReais, rotuloCompetencia } from "@/lib/format";

export default function FichaEmpresaPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const empresa = useQuery({ queryKey: ["empresa", id], queryFn: () => obterEmpresa(id) });

  if (empresa.isPending) return <Carregando />;
  if (empresa.isError) return <Erro texto="Empresa não encontrada." />;
  const e = empresa.data;

  async function alternarAtivo() {
    await atualizarEmpresa(id, { ativo: !e.ativo });
    await queryClient.invalidateQueries({ queryKey: ["empresa", id] });
    await queryClient.invalidateQueries({ queryKey: ["empresas"] });
  }

  return (
    <section className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">{e.nome}</h1>
          <p className="font-mono text-xs text-zinc-500">{e.cnpj_formatado}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <PacoteBadge pacote={e.pacote} />
            {e.sujeita_fator_r ? (
              <Badge cor="azul">sujeita a Fator R</Badge>
            ) : (
              <Badge>fora do Fator R</Badge>
            )}
            {e.ativo ? <Badge cor="verde">ativa</Badge> : <Badge>inativa</Badge>}
          </div>
          <p className="mt-2 text-sm text-zinc-600">
            Honorário do pacote: {formatarReais(e.honorario_mensal)} · Início de atividade:{" "}
            {e.inicio_atividade ? rotuloCompetencia(e.inicio_atividade) : "não informado"}
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <Link href={`/empresas/${id}/editar`} className="rounded border px-3 py-1.5">
            Editar
          </Link>
          <button type="button" onClick={alternarAtivo} className="rounded border px-3 py-1.5">
            {e.ativo ? "Desativar" : "Reativar"}
          </button>
        </div>
      </div>

      {e.sujeita_fator_r && (
        <div className="space-y-2">
          <h2 className="font-semibold">Fator R</h2>
          <PainelFatorR companyId={id} />
        </div>
      )}

      {e.sujeita_fator_r && (
        <div className="space-y-2">
          <h2 className="font-semibold">Simulador de correção</h2>
          <Simulador companyId={id} />
        </div>
      )}

      {e.sujeita_fator_r && (
        <Chat
          titulo={`Consultor · ${e.nome}`}
          placeholder="Pergunte sobre esta empresa (situação, simulação, explicação)"
          testid="chat-consultor-ficha"
          enviar={(m) => perguntarConsultor(m, id)}
        />
      )}

      <div className="space-y-2">
        <h2 className="font-semibold">Movimentos mensais</h2>
        <GradeMensal companyId={id} />
      </div>
    </section>
  );
}
