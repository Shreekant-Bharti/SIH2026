import { Database, MapPinned, Settings2, Target } from "lucide-react";

const details = [
  { label: "Model", value: "Ridge Residual", icon: Settings2 },
  { label: "Prediction target", value: "Panchayat rainfall", icon: Target },
  { label: "Model coverage", value: "Dhanbad District, Jharkhand", icon: MapPinned },
  { label: "Feature processing", value: "Backend pipeline", icon: Database },
];

export function ModelInformation() {
  return <section aria-labelledby="model-information-title"><div className="mb-3"><p className="eyebrow">Scientific transparency</p><h2 id="model-information-title" className="section-title">Model information</h2></div><div className="scientific-panel grid sm:grid-cols-2 xl:grid-cols-4">{details.map(({ label, value, icon: Icon }, index) => <div className={`p-4 ${index > 0 ? "border-t border-border sm:border-l sm:border-t-0" : ""} ${index === 2 ? "sm:border-l-0 xl:border-l" : ""} ${index > 1 ? "sm:border-t xl:border-t-0" : ""}`} key={label}><Icon className="size-4 text-primary"/><p className="metric-label mt-3">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>)}</div><p className="mt-2 text-xs leading-5 text-muted-foreground">Reference: project coarse rainfall dataset · Version: <span className="font-mono">Ridge_Residual_v1</span> · Input feature engineering is owned by the model service.</p></section>;
}