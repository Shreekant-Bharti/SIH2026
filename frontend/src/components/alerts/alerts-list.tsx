import { ShieldCheck } from "lucide-react";

export function AlertsList() {
  return <section aria-labelledby="alerts-title"><div className="mb-3"><p className="eyebrow">Decision-support context</p><h2 id="alerts-title" className="section-title">Rainfall risk & advisory</h2></div><div className="scientific-panel grid min-h-48 place-items-center px-5 py-8 text-center" role="status"><div className="max-w-lg"><ShieldCheck className="mx-auto size-5 text-primary" /><p className="metric-label mt-3">No live alerts available</p><p className="mt-2 text-sm leading-6 text-muted-foreground">Operational alert-generation logic is not connected. MonsoonScope does not issue official warnings or fabricate local recommendations.</p></div></div></section>;
}