import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { CloudRain } from "lucide-react";
import { LocationControls } from "@/components/location/location-controls";
import { ProductPage } from "@/components/pages/product-page";
import { useGeographicSelection } from "@/hooks/use-geographic-selection";
import {
  backendClient,
  type BackendPredictionResult,
  type BackendValidationMetrics,
} from "@/services/backend-client";

type PredictionDisplay = BackendPredictionResult & {
  observed_rainfall_mm: number | null;
  prediction_error_mm: number | null;
};

function PredictionsPage() {
  const location = useGeographicSelection();
  const selectedPanchayat = location.selection.panchayat;
  const gpcode = selectedPanchayat?.code;
  const [date, setDate] = useState("");
  const [prediction, setPrediction] = useState<PredictionDisplay>();
  const [predictionState, setPredictionState] = useState<"idle" | "loading" | "error">("idle");
  const [predictionError, setPredictionError] = useState<string>();
  const [validation, setValidation] = useState<BackendValidationMetrics>();
  const [validationState, setValidationState] = useState<
    "idle" | "loading" | "available" | "unavailable"
  >("idle");

  useEffect(() => {
    setPrediction(undefined);
    setPredictionError(undefined);
    setPredictionState("idle");
    if (!gpcode) {
      setValidation(undefined);
      setValidationState("idle");
      return;
    }

    let active = true;
    setValidation(undefined);
    setValidationState("loading");
    void backendClient
      .getValidation(gpcode)
      .then((metrics) => {
        if (!active) return;
        setValidation(metrics);
        setValidationState("available");
      })
      .catch(() => {
        if (!active) return;
        setValidation(undefined);
        setValidationState("unavailable");
      });
    return () => {
      active = false;
    };
  }, [gpcode]);

  async function generatePrediction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPanchayat || !date) return;
    setPrediction(undefined);
    setPredictionError(undefined);
    setPredictionState("loading");
    try {
      const input = await backendClient.getPredictionInput(selectedPanchayat.code, date);
      const result = await backendClient.predict(input);
      const observation = input.observed_rainfall_mm;
      setPrediction({
        ...result,
        observed_rainfall_mm: observation,
        prediction_error_mm:
          observation === null
            ? null
            : Number((result.predicted_rainfall_mm - observation).toFixed(2)),
      });
      setPredictionState("idle");
    } catch (cause) {
      setPredictionError(cause instanceof Error ? cause.message : "Prediction request failed.");
      setPredictionState("error");
    }
  }

  return (
    <ProductPage
      eyebrow="Historical validation / model demonstration"
      title="Panchayat rainfall prediction"
      description="Select a Dhanbad Panchayat and a date in 2024. Real historical inputs are retrieved from the project dataset and passed to the existing Ridge Residual model. This is not an operational forecast."
    >
      <LocationControls
        selection={location.selection}
        options={location.options}
        onSelect={location.select}
      />
      <div className="grid gap-8">
        <form
          onSubmit={generatePrediction}
          className="flex flex-wrap items-end gap-3 border-b border-border py-5"
        >
          <label className="grid gap-1 text-[11px] font-bold uppercase text-muted-foreground">
            <span>Validation date</span>
            <input
              aria-label="Validation date"
              className="h-10 rounded-md border border-input bg-background px-3 text-sm font-medium text-foreground"
              type="date"
              min="2024-01-01"
              max="2024-12-31"
              value={date}
              onChange={(event) => {
                setDate(event.target.value);
                setPrediction(undefined);
                setPredictionError(undefined);
                setPredictionState("idle");
              }}
              required
            />
          </label>
          <button
            className="flex h-10 items-center gap-2 border border-primary bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            type="submit"
            disabled={!selectedPanchayat || !date || predictionState === "loading"}
          >
            <CloudRain className="size-4" />
            {predictionState === "loading" ? "Generating..." : "Generate Prediction"}
          </button>
          <p className="w-full text-xs text-muted-foreground">
            Available dates are constrained to 2024, the historical evaluation period. Weather and
            terrain inputs come from the real project dataset.
          </p>
        </form>

        <section aria-labelledby="model-prediction-title">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="eyebrow">Existing backend inference</p>
              <h2 id="model-prediction-title" className="section-title">
                Model prediction
              </h2>
            </div>
            {prediction && (
              <span className="status-badge">
                {prediction.model.replaceAll("_", " ")} · {prediction.model_version}
              </span>
            )}
          </div>
          {predictionState === "loading" ? (
            <div className="scientific-panel p-5 text-sm" role="status">
              Retrieving source inputs and running Ridge Residual...
            </div>
          ) : predictionState === "error" ? (
            <div
              className="border border-destructive bg-card p-5 text-sm text-destructive"
              role="alert"
            >
              {predictionError ?? "Prediction failed."}
            </div>
          ) : prediction ? (
            <div className="scientific-panel grid grid-cols-1 divide-y divide-border sm:grid-cols-2 sm:divide-x sm:divide-y-0">
              <PredictionValue
                label="Reference rainfall"
                value={formatMillimetres(prediction.reference_rainfall_mm)}
                note="ERA5-Land historical input"
              />
              <PredictionValue
                label="ML predicted rainfall"
                value={formatMillimetres(prediction.predicted_rainfall_mm)}
                note="Ridge Residual model output"
              />
              <PredictionValue
                label="Observed rainfall"
                value={formatMillimetres(prediction.observed_rainfall_mm)}
                note={
                  prediction.observed_rainfall_mm === null
                    ? "Observation unavailable"
                    : "CHIRPS target"
                }
              />
              <PredictionValue
                label="Prediction error"
                value={formatMillimetres(prediction.prediction_error_mm, true)}
                note="Predicted − observed; positive means overprediction"
              />
            </div>
          ) : (
            <div className="scientific-panel p-5 text-sm text-muted-foreground" role="status">
              Select a Panchayat and 2024 date, then generate a model prediction.
            </div>
          )}
          {prediction && (
            <p className="mt-2 text-xs text-muted-foreground">
              Prediction generated from the existing model. Historical demonstration only; not a
              live forecast.
            </p>
          )}
        </section>

        <section aria-labelledby="validation-metrics-title">
          <div className="mb-3">
            <p className="eyebrow">Stored model evaluation</p>
            <h2 id="validation-metrics-title" className="section-title">
              2024 validation
            </h2>
          </div>
          {validationState === "loading" ? (
            <div className="scientific-panel p-5 text-sm" role="status">
              Loading stored validation metrics...
            </div>
          ) : validationState === "available" && validation ? (
            <div className="scientific-panel grid grid-cols-2 divide-x divide-y divide-border sm:grid-cols-3 xl:grid-cols-5">
              <ValidationValue label="ML RMSE" value={formatMillimetres(validation.rmse)} />
              <ValidationValue
                label="Baseline RMSE"
                value={formatMillimetres(validation.baseline_rmse)}
              />
              <ValidationValue label="ML MAE" value={formatMillimetres(validation.mae)} />
              <ValidationValue
                label="Baseline MAE"
                value={formatMillimetres(validation.baseline_mae)}
              />
              <ValidationValue label="R²" value={validation.r2.toFixed(2)} />
            </div>
          ) : validationState === "unavailable" ? (
            <div className="scientific-panel p-5 text-sm text-muted-foreground" role="status">
              Validation metrics are unavailable for this Panchayat because observed target records
              are missing or the backend could not be reached.
            </div>
          ) : (
            <div className="scientific-panel p-5 text-sm text-muted-foreground" role="status">
              Select a Panchayat to load its stored 2024 validation metrics.
            </div>
          )}
          {validationState === "available" && (
            <p className="mt-2 text-xs text-muted-foreground">
              Baseline is reference rainfall compared with observed rainfall. Metrics come from the
              stored 2024 evaluation artifact.
            </p>
          )}
        </section>
      </div>
    </ProductPage>
  );
}

function PredictionValue({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="p-5">
      <p className="metric-label">{label}</p>
      <p className="mt-2 font-mono text-xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}

function ValidationValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4">
      <p className="metric-label">{label}</p>
      <p className="mt-2 font-mono text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatMillimetres(value: number | null, signed = false): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)} mm`;
}

export const Route = createFileRoute("/predictions")({
  head: () => ({
    meta: [
      { title: "Panchayat Rainfall Prediction — MonsoonScope" },
      {
        name: "description",
        content: "Run the existing Ridge Residual model with historical Dhanbad Panchayat inputs.",
      },
      { property: "og:title", content: "Panchayat Rainfall Prediction — MonsoonScope" },
      {
        property: "og:description",
        content: "Historical validation mode for Panchayat rainfall downscaling.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: PredictionsPage,
});
