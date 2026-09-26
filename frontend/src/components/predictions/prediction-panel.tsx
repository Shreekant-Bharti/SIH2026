import { ArrowDown, Database, MapPin, SlidersHorizontal } from "lucide-react";
import { DataStatePanel } from "@/components/scientific/data-state";
import type { RainfallIntelligence } from "@/types/monsoon";

const UNAVAILABLE_DATA: RainfallIntelligence = {
  state: "empty",
  locationId: "unselected",
  coverage: "unavailable",
  modelName: "Ridge Residual",
  modelVersion: "Ridge_Residual_v1",
  target: "Panchayat rainfall",
  history: [],
  message: "Select a supported Panchayat to request rainfall intelligence.",
};

type PredictionPanelProps = {
  data?: RainfallIntelligence;
  /** Keeps the panel safe while an older preview module is being hot-replaced. */
  predictions?: RainfallIntelligence;
};

export function PredictionPanel({ data, predictions }: PredictionPanelProps) {
  const intelligence = data ?? predictions ?? UNAVAILABLE_DATA;
  const reference = intelligence.values?.referenceMm;
  const predicted = intelligence.values?.predictedMm;
  const difference = intelligence.values?.differenceMm;
  return (
    <section aria-labelledby="prediction-title">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Core model contribution</p>
          <h2 id="prediction-title" className="section-title">
            Reference vs downscaled
          </h2>
        </div>
        <span className="status-badge">{intelligence.modelName}</span>
      </div>
      {intelligence.state !== "success" ? (
        <DataStatePanel
          state={intelligence.state}
          title={intelligence.state === "unsupported" ? "No model data" : "Prediction unavailable"}
          message={intelligence.message}
        />
      ) : (
        <div className="scientific-panel grid overflow-hidden lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
          <Metric
            icon={Database}
            label="Reference rainfall"
            value={reference === undefined ? "—" : `${reference} mm`}
            note={
              intelligence.values?.date
                ? `Historical record · ${intelligence.values.date}`
                : "Coarse / reference input"
            }
          />
          <ArrowDown className="m-auto size-4 rotate-0 text-muted-foreground lg:-rotate-90" />
          <Metric
            icon={SlidersHorizontal}
            label="Ridge Residual"
            value="Downscaling"
            note="Feature processing: backend pipeline"
          />
          <ArrowDown className="m-auto size-4 rotate-0 text-muted-foreground lg:-rotate-90" />
          <Metric
            icon={MapPin}
            label="Panchayat rainfall"
            value={predicted === undefined ? "—" : `${predicted} mm`}
            note={
              difference === undefined
                ? "Difference unavailable"
                : `${difference > 0 ? "+" : ""}${difference} mm vs reference`
            }
          />
        </div>
      )}
    </section>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  note,
}: {
  icon: typeof Database;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="p-5">
      <Icon className="size-4 text-primary" />
      <p className="metric-label mt-4">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}
