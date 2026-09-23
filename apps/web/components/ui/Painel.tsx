import type { HTMLAttributes } from "react";

export function Painel({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`border-line bg-panel rounded-[10px] border p-4 shadow-[0_20px_60px_-30px_rgba(0,0,0,.8),inset_0_1px_0_rgba(255,255,255,.04)] ${className}`}
      {...props}
    />
  );
}
