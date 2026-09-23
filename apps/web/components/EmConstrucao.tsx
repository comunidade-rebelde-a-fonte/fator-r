import { TituloPagina } from "@/components/ui/TituloPagina";

export function EmConstrucao({ titulo }: { titulo: string }) {
  return (
    <section>
      <TituloPagina>{titulo}</TituloPagina>
      <p className="text-muted mt-2 text-sm">Em construção.</p>
    </section>
  );
}
