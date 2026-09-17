import { Badge } from "@/components/ui/Badge";

const STATUS = {
  ok: { rotulo: "ok", cor: "verde" },
  error: { rotulo: "erro", cor: "vermelho" },
  needs_review: { rotulo: "revisão", cor: "amarelo" },
} as const;

export function StatusTraceBadge({ status }: { status: keyof typeof STATUS }) {
  return <Badge cor={STATUS[status].cor}>{STATUS[status].rotulo}</Badge>;
}
