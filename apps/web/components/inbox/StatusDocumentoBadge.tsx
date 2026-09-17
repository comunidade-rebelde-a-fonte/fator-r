import { Badge, type CorBadge } from "@/components/ui/Badge";
import type { StatusDocumento } from "@/lib/api/types";

export const STATUS_DOCUMENTO: Record<StatusDocumento, { rotulo: string; cor: CorBadge }> = {
  received: { rotulo: "recebido", cor: "cinza" },
  parsed: { rotulo: "extraído", cor: "azul" },
  needs_review: { rotulo: "revisão", cor: "amarelo" },
  linked: { rotulo: "vinculado", cor: "verde" },
  rejected: { rotulo: "rejeitado", cor: "vermelho" },
};

export function StatusDocumentoBadge({ status }: { status: StatusDocumento }) {
  return <Badge cor={STATUS_DOCUMENTO[status].cor}>{STATUS_DOCUMENTO[status].rotulo}</Badge>;
}
