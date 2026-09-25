import { INDIA, geographyService } from "@/services/geography-service";
import type { RegionMeta } from "@/types/geography";
import type { RainfallIntelligence } from "@/types/monsoon";

/**
 * Rainfall/model access boundary. The FastAPI contract is not connected yet,
 * so this service returns explicit availability states and never fabricates a
 * prediction. Backend-owned feature engineering stays outside the frontend.
 */
const resolve = (regionOrId?: RegionMeta | string): RegionMeta => {
  if (!regionOrId) return INDIA;
  if (typeof regionOrId === "string") return geographyService.getRegion(regionOrId) ?? INDIA;
  return regionOrId;
};

export const monsoonService = {
  getRainfallIntelligence(region?: RegionMeta | string): RainfallIntelligence {
    const selected = resolve(region);
    const chain = geographyService.getAncestors(selected);
    const inDhanbad = chain.some((item) => item.level === "district" && item.id === "dhanbad--jharkhand");
    const coverage = selected.id === "dhanbad--jharkhand" || inDhanbad ? "available" : "unavailable";

    if (coverage === "unavailable") {
      return { state: "unsupported", locationId: selected.id, coverage, modelName: "Ridge Residual", modelVersion: "Ridge_Residual_v1", target: "Panchayat rainfall", history: [], message: "Model data is not currently available for this location." };
    }
    if (selected.level !== "panchayat") {
      return { state: "empty", locationId: selected.id, coverage, modelName: "Ridge Residual", modelVersion: "Ridge_Residual_v1", target: "Panchayat rainfall", history: [], message: "Select a Panchayat in Dhanbad to request localized rainfall intelligence." };
    }
    return { state: "empty", locationId: selected.id, coverage, modelName: "Ridge Residual", modelVersion: "Ridge_Residual_v1", target: "Panchayat rainfall", history: [], message: "Prediction unavailable until the FastAPI model service is connected." };
  },
};
