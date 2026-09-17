import { Badge } from "@/components/ui/Badge";
import type { Semaforo } from "@/lib/api/types";

const SEMAFORO: Record<Semaforo, { rotulo: string; cor: "vermelho" | "amarelo" | "verde" }> = {
  vermelho: { rotulo: "Vermelho · < 28% (Anexo V)", cor: "vermelho" },
  amarelo: { rotulo: "Amarelo · no limite", cor: "amarelo" },
  verde: { rotulo: "Verde · na meta", cor: "verde" },
};

export function SemaforoBadge({ semaforo }: { semaforo: Semaforo | null }) {
  if (!semaforo) return <Badge>Dados insuficientes</Badge>;
  return <Badge cor={SEMAFORO[semaforo].cor}>{SEMAFORO[semaforo].rotulo}</Badge>;
}
