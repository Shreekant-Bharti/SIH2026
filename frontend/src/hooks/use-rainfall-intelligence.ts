import { useEffect, useState } from "react";
import { monsoonService } from "@/services/monsoon-service";
import type { RegionMeta } from "@/types/geography";
import type { RainfallIntelligence } from "@/types/monsoon";

export function useRainfallIntelligence(region: RegionMeta): RainfallIntelligence {
  const [data, setData] = useState<RainfallIntelligence>({
    state: "loading",
    locationId: region.id,
    coverage: "unavailable",
    modelName: "Ridge Residual",
    modelVersion: "Ridge_Residual_v1",
    target: "Panchayat rainfall",
    history: [],
    message: "Loading rainfall data...",
  });

  useEffect(() => {
    let active = true;
    setData({
      state: "loading",
      locationId: region.id,
      coverage: "unavailable",
      modelName: "Ridge Residual",
      modelVersion: "Ridge_Residual_v1",
      target: "Panchayat rainfall",
      history: [],
      message: "Loading rainfall data...",
    });
    void monsoonService.getRainfallIntelligence(region).then((result) => {
      if (active) setData(result);
    });
    return () => {
      active = false;
    };
  }, [region]);

  return data;
}
