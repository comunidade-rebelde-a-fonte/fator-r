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
    <nav aria-label="Navegação principal" className="flex h-full gap-1">
      {ITENS.map((item) => {
        const ativo = pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={ativo ? "page" : undefined}
            className={`flex items-center border-b-2 px-3 text-sm transition-colors ${
              ativo ? "border-accent text-fg" : "text-muted hover:text-fg border-transparent"
            }`}
          >
            {item.rotulo}
          </Link>
        );
      })}
    </nav>
  );
}
