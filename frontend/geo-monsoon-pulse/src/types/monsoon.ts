export type { Bounds, RegionLevel, RegionMeta, RegionSelection } from "@/types/geography";

export type DataState = "loading" | "success" | "empty" | "unsupported" | "error";

export interface RainfallPoint {
  date: string;
  referenceMm?: number;
  predictedMm?: number;
  observedMm?: number;
  cumulativeMm?: number;
}

export interface RainfallValues {
  referenceMm?: number;
  predictedMm?: number;
  differenceMm?: number;
  observedMm?: number;
  date?: string;
}

export interface RainfallIntelligence {
  state: DataState;
  locationId: string;
  coverage: "available" | "unavailable";
  modelName: "Ridge Residual";
  modelVersion: "Ridge_Residual_v1";
  target: "Panchayat rainfall";
  values?: RainfallValues;
  history: RainfallPoint[];
  message: string;
}
