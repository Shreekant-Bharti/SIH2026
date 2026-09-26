import { INDIA, geographyService } from "@/services/geography-service";
import { backendClient } from "@/services/backend-client";
import type { RegionMeta } from "@/types/geography";
import type { RainfallIntelligence, RainfallPoint } from "@/types/monsoon";

/**
 * Rainfall/model access boundary. Historical predictions and model feature
 * engineering remain owned by the FastAPI backend.
 */
const resolve = (regionOrId?: RegionMeta | string): RegionMeta => {
  if (!regionOrId) return INDIA;
  if (typeof regionOrId === "string") return geographyService.getRegion(regionOrId) ?? INDIA;
  return regionOrId;
};

export const monsoonService = {
  async getRainfallIntelligence(region?: RegionMeta | string): Promise<RainfallIntelligence> {
    const selected = resolve(region);
    const chain = geographyService.getAncestors(selected);
    const inDhanbad = chain.some(
      (item) => item.level === "district" && item.id === "dhanbad--jharkhand",
    );
    const coverage =
      selected.id === "dhanbad--jharkhand" || inDhanbad ? "available" : "unavailable";

    if (coverage === "unavailable") {
      return {
        state: "unsupported",
        locationId: selected.id,
        coverage,
        modelName: "Ridge Residual",
        modelVersion: "Ridge_Residual_v1",
        target: "Panchayat rainfall",
        history: [],
        message: "Model data is not currently available for this location.",
      };
    }
    if (selected.level !== "panchayat") {
      return {
        state: "empty",
        locationId: selected.id,
        coverage,
        modelName: "Ridge Residual",
        modelVersion: "Ridge_Residual_v1",
        target: "Panchayat rainfall",
        history: [],
        message: "Select a Panchayat in Dhanbad to request localized rainfall intelligence.",
      };
    }
    try {
      const response = await backendClient.getHistory(selected.code);
      const history: RainfallPoint[] = response.data.map((item) => ({
        date: item.date,
        referenceMm: item.reference_rainfall_mm,
        predictedMm: item.predicted_rainfall_mm,
        observedMm: item.observed_rainfall_mm ?? undefined,
      }));
      const latest = history.at(-1);
      if (!latest) {
        return {
          state: "empty",
          locationId: selected.id,
          coverage,
          modelName: "Ridge Residual",
          modelVersion: "Ridge_Residual_v1",
          target: "Panchayat rainfall",
          history,
          message: "The backend has no historical test records for this Panchayat.",
        };
      }
      return {
        state: "success",
        locationId: selected.id,
        coverage,
        modelName: "Ridge Residual",
        modelVersion: "Ridge_Residual_v1",
        target: "Panchayat rainfall",
        values: {
          date: latest.date,
          referenceMm: latest.referenceMm,
          predictedMm: latest.predictedMm,
          differenceMm: Number((latest.predictedMm! - latest.referenceMm!).toFixed(2)),
          observedMm: latest.observedMm,
        },
        history,
        message: `Historical backend results through ${latest.date}.`,
      };
    } catch (cause) {
      return {
        state: "error",
        locationId: selected.id,
        coverage,
        modelName: "Ridge Residual",
        modelVersion: "Ridge_Residual_v1",
        target: "Panchayat rainfall",
        history: [],
        message: cause instanceof Error ? cause.message : "Could not reach the rainfall backend.",
      };
    }
  },
};
