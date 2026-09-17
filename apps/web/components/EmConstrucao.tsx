export function EmConstrucao({ titulo }: { titulo: string }) {
  return (
    <section>
      <h1 className="text-xl font-semibold">{titulo}</h1>
      <p className="mt-2 text-sm text-zinc-500">Em construção.</p>
    </section>
  );
}
