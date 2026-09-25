import type { ReactNode } from "react";
import { SourceFooter } from "@/components/scientific/source-footer";

export function ProductPage({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return <main className="min-h-[calc(100vh-120px)]"><header className="border-b border-border bg-card"><div className="mx-auto max-w-[1600px] px-4 py-7 lg:px-6"><div className="flex flex-wrap items-end justify-between gap-5"><div><p className="eyebrow">{eyebrow}</p><h1 className="mt-2 max-w-4xl text-2xl font-bold text-foreground md:text-3xl">{title}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p></div><span className="status-badge">Dhanbad model coverage</span></div></div></header><div className="mx-auto max-w-[1600px] px-4 py-7 lg:px-6">{children}<SourceFooter /></div></main>;
}