import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { INDIA, geographyService } from "@/services/geography-service";
import type { RegionMeta, RegionSelection } from "@/types/geography";

/** Single source of truth for the India → state → district → block → panchayat selection. */
export function useGeographicSelection() {
  const [raw, setSelection] = useState<RegionSelection>({ country: INDIA });
  const version = useSyncExternalStore(geographyService.subscribe, geographyService.getVersion, () => 0);

  // Re-resolve by stable id so geometry upgrades (e.g. block polygons loaded later) are reflected.
  const selection = useMemo<RegionSelection>(() => {
    const fresh = (r?: RegionMeta) => (r ? geographyService.getRegion(r.id) ?? r : undefined);
    const out: RegionSelection = { country: INDIA };
    const [state, district, block, panchayat] = [fresh(raw.state), fresh(raw.district), fresh(raw.block), fresh(raw.panchayat)];
    if (state) out.state = state;
    if (district) out.district = district;
    if (block) out.block = block;
    if (panchayat) out.panchayat = panchayat;
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw, version]);

  const current = selection.panchayat ?? selection.block ?? selection.district ?? selection.state ?? selection.country;

  // Block points load lazily once the user leaves the India view; block polygons per district.
  useEffect(() => {
    if (selection.state) void geographyService.loadBlocks().catch((e: unknown) => console.warn("[Geography]", e));
  }, [selection.state]);
  const districtId = selection.district?.id;
  useEffect(() => {
    if (districtId) void geographyService.loadBlockBoundaries(districtId).catch((e: unknown) => console.warn("[Geography]", e));
  }, [districtId]);

  const select = useCallback((region?: RegionMeta) => {
    if (!region || region.level === "country") {
      setSelection({ country: INDIA });
      return;
    }
    const next: RegionSelection = { country: INDIA };
    for (const ancestor of geographyService.getAncestors(region)) {
      if (ancestor.level === "state") next.state = ancestor;
      if (ancestor.level === "district") next.district = ancestor;
      if (ancestor.level === "block") next.block = ancestor;
      if (ancestor.level === "panchayat") next.panchayat = ancestor;
    }
    if (import.meta.env.DEV) console.info("[Map] Selected location:", geographyService.getAncestors(region).map((r) => r.name).join(" › "));
    setSelection(next);
  }, []);

  const reset = useCallback(() => setSelection({ country: INDIA }), []);

  const options = useMemo(
    () => ({
      states: geographyService.getStates(),
      districts: selection.state ? geographyService.getDistricts(selection.state.id) : [],
      blocks: selection.district ? geographyService.getBlocks(selection.district.id) : [],
      panchayats: selection.block ? geographyService.getPanchayats(selection.block.id) : [],
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selection.state, selection.district, selection.block, version],
  );

  return { selection, current, options, select, reset, blocksLoaded: geographyService.isBlocksLoaded() };
}
