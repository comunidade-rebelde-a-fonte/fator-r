import { Badge, type CorBadge } from "@/components/ui/Badge";
import type { Origem, Pacote } from "@/lib/api/types";

const PACOTES: Record<Pacote, { rotulo: string; cor: CorBadge }> = {
  monitoramento: { rotulo: "Monitoramento", cor: "azul" },
  correcao: { rotulo: "Correção", cor: "roxo" },
  retainer: { rotulo: "Retainer", cor: "verde" },
};

export function PacoteBadge({ pacote }: { pacote: Pacote | null }) {
  if (!pacote) return <Badge>Sem pacote</Badge>;
  return <Badge cor={PACOTES[pacote].cor}>{PACOTES[pacote].rotulo}</Badge>;
}

const ORIGENS: Record<Origem, { rotulo: string; cor: CorBadge }> = {
  manual: { rotulo: "manual", cor: "cinza" },
  pgdas: { rotulo: "pgdas", cor: "azul" },
  folha: { rotulo: "folha", cor: "verde" },
  agente: { rotulo: "agente", cor: "roxo" },
};

export function OrigemBadge({ origem }: { origem: Origem }) {
  return <Badge cor={ORIGENS[origem].cor}>{ORIGENS[origem].rotulo}</Badge>;
}
