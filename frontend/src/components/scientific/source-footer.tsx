import { Database, FlaskConical } from "lucide-react";

export function SourceFooter({ compact = false }: { compact?: boolean }) {
  return (
    <aside
      className={`source-strip ${compact ? "mt-5" : "mt-8"}`}
      aria-label="Data sources and status"
    >
      <div className="flex items-start gap-3">
        <Database className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <p className="metric-label">Data sources</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Administrative boundaries: geoBoundaries / DataMeet and LGD 2024. Project Panchayat
            metadata and historical rainfall/model records are served by the Dhanbad backend and
            keyed by GPCODE.
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 border-t border-border pt-3 text-xs font-semibold text-foreground sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
        <FlaskConical className="size-4 text-primary" />
        Demonstration data · Not an official forecast
      </div>
    </aside>
  );
}
