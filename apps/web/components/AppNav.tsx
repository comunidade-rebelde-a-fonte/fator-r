"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITENS = [
  { href: "/carteira", rotulo: "Carteira" },
  { href: "/empresas", rotulo: "Empresas" },
  { href: "/inbox", rotulo: "Inbox" },
  { href: "/agentes", rotulo: "Agentes" },
  { href: "/observabilidade", rotulo: "Observabilidade" },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Navegação principal" className="flex gap-1">
      {ITENS.map((item) => {
        const ativo = pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={ativo ? "page" : undefined}
            className={`rounded px-3 py-1.5 text-sm ${
              ativo ? "bg-zinc-900 text-white" : "text-zinc-700 hover:bg-zinc-100"
            }`}
          >
            {item.rotulo}
          </Link>
        );
      })}
    </nav>
  );
}
