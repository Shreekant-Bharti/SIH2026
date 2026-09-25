import type { StyleSpecification } from "maplibre-gl";
import type { Bounds } from "@/types/geography";

/** Local MapLibre style using public raster tiles. No API key required. */
export const MAP_STYLE_URL: StyleSpecification = {
  version: 8,
  glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    { id: "basemap-background", type: "background", paint: { "background-color": "#edf1f2" } },
    { id: "basemap", type: "raster", source: "osm", paint: { "raster-saturation": -0.65, "raster-contrast": -0.08, "raster-opacity": 0.9 } },
  ],
};

/** Fallback: OpenStreetMap standard raster tiles (desaturated), used once if the primary style fails. */
export const FALLBACK_STYLE = "https://tiles.openfreemap.org/styles/positron";

export const INDIA_BOUNDS: Bounds = [
  [68.1, 6.5],
  [97.42, 35.7],
];
export const DEFAULT_CENTER: [number, number] = [82.8, 22.0];
export const DEFAULT_ZOOM = 3.8;
export const MAX_BOUNDS: Bounds = [
  [64.0, 4.0],
  [100.0, 38.5],
];
export const MIN_ZOOM = 3.2;
/** How long to wait for the primary style before switching to the fallback. */
export const STYLE_TIMEOUT_MS = 12000;
export const POINT_ZOOM = { block: 11, panchayat: 13.5 } as const;
export const LABEL_FONT = ["Noto Sans Regular"];
