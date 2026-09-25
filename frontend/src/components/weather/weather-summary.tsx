import { Activity, CloudRain, Database, GitCompareArrows } from "lucide-react";
import type { RainfallIntelligence } from "@/types/monsoon";

export function WeatherSummary({ data }: { data: RainfallIntelligence }) {
  const items = [
    { label: "Reference rainfall", value: data.values?.referenceMm === undefined ? "—" : `${data.values.referenceMm} mm`, note: "Reference dataset", icon: Database },
    { label: "Predicted rainfall", value: data.values?.predictedMm === undefined ? "—" : `${data.values.predictedMm} mm`, note: "Panchayat downscaled", icon: CloudRain },
    { label: "Downscaling difference", value: data.values?.differenceMm === undefined ? "—" : `${data.values.differenceMm > 0 ? "+" : ""}${data.values.differenceMm} mm`, note: "Versus reference", icon: GitCompareArrows },
    { label: "Model status", value: data.state === "success" ? "Available" : "Unavailable", note: data.modelVersion, icon: Activity },
  ];
  return <section aria-labelledby="conditions-title">
    <div className="mb-3 flex items-end justify-between"><div><p className="eyebrow">Current rainfall intelligence</p><h2 id="conditions-title" className="section-title">Key rainfall metrics</h2></div><p className="max-w-56 text-right text-xs text-muted-foreground">Backend values appear when available</p></div>
    <div className="grid grid-cols-2 overflow-hidden rounded-md border border-border bg-card sm:grid-cols-4">
      {items.map(({ label, value, note, icon: Icon }, index) => <div className={`p-4 ${index > 0 ? "border-l border-border" : ""} ${index === 2 ? "max-sm:border-l-0" : ""} ${index > 1 ? "max-sm:border-t" : ""}`} key={label}>
        <div className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase text-muted-foreground"><Icon className="size-4 text-primary" />{label}</div>
        <p className="font-mono text-xl font-semibold text-foreground">{value}</p><p className="mt-1 text-[10px] text-muted-foreground">{note}</p>
      </div>)}
    </div>
  </section>;
}