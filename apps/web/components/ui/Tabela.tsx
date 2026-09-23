import type { HTMLAttributes, TableHTMLAttributes } from "react";

export function Tabela({ className = "", ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <table className={`w-full text-left text-sm [&_td]:px-2 [&_th]:px-2 ${className}`} {...props} />
  );
}

export function CabecalhoTabela({
  className = "",
  ...props
}: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={`text-muted border-b text-[11px] tracking-[.1em] uppercase ${className}`}
      {...props}
    />
  );
}
