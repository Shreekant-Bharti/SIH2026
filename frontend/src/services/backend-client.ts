const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

async function errorMessage(response: Response): Promise<string> {
  const body = await response.text();
  try {
    const payload = JSON.parse(body) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // Preserve non-JSON error responses for the UI.
  }
  return body || `Backend request failed (${response.status})`;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json() as Promise<T>;
}

export interface BackendPanchayat {
  gpcode: number;
  name: string;
}

export interface BackendHistoryItem {
  date: string;
  observed_rainfall_mm: number | null;
  reference_rainfall_mm: number;
  predicted_rainfall_mm: number;
}

export interface BackendPredictionInput {
  gpcode: number;
  date: string;
  temperature: number;
  humidity: number;
  wind: number;
  et: number;
  elevation: number;
  slope: number;
  landcover: number;
  reference_rainfall: number;
  observed_rainfall_mm: number | null;
}

export interface BackendPredictionResult {
  gpcode: number;
  date: string;
  predicted_rainfall_mm: number;
  reference_rainfall_mm: number;
  model: string;
  model_version: string;
}

export interface BackendValidationMetrics {
  gpcode: number;
  rmse: number;
  mae: number;
  r2: number;
  bias: number;
  correlation: number;
  baseline_rmse: number;
  baseline_mae: number;
  model_rmse: number;
}

export const backendClient = {
  getHealth: () => get<{ status: string; model_loaded: boolean }>("/health"),
  getBlocks: (district = "Dhanbad") =>
    get<{ blocks: string[] }>(`/blocks?district=${encodeURIComponent(district)}`),
  getPanchayats: (block: string) =>
    get<{ panchayats: BackendPanchayat[] }>(`/panchayats?block=${encodeURIComponent(block)}`),
  getHistory: (gpcode: string) =>
    get<{ data: BackendHistoryItem[] }>(`/history/${encodeURIComponent(gpcode)}`),
  getPredictionInput: (gpcode: string, date: string) =>
    get<BackendPredictionInput>(
      `/input/${encodeURIComponent(gpcode)}?date=${encodeURIComponent(date)}`,
    ),
  predict: (input: BackendPredictionInput) =>
    post<BackendPredictionResult>("/predict", {
      gpcode: input.gpcode,
      date: input.date,
      temperature: input.temperature,
      humidity: input.humidity,
      wind: input.wind,
      et: input.et,
      elevation: input.elevation,
      slope: input.slope,
      landcover: input.landcover,
      reference_rainfall: input.reference_rainfall,
    }),
  getValidation: (gpcode: string) =>
    get<BackendValidationMetrics>(`/validation/${encodeURIComponent(gpcode)}`),
};
