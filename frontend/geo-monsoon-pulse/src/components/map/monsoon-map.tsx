import { useCallback, useEffect, useRef, useState } from "react";
import type { GeoJSONSource, Map as MlMap, MapLayerMouseEvent } from "maplibre-gl";
import { Layers3, LocateFixed, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FALLBACK_STYLE, INDIA_BOUNDS, LABEL_FONT, MAP_STYLE_URL, MAX_BOUNDS, MIN_ZOOM, POINT_ZOOM, STYLE_TIMEOUT_MS } from "@/config/map-config";
import { GEO_ATTRIBUTION, LEVEL_LABEL, geographyService } from "@/services/geography-service";
import type { Bounds, RegionFeatureCollection, RegionLevel, RegionMeta } from "@/types/geography";

export interface ClickedLocation {
  longitude: number;
  latitude: number;
  /** Detection result from exact point-in-polygon tests; undefined while detecting. */
  detected?: { chain: RegionMeta[]; region?: RegionMeta; blockMissing: boolean };
}

interface Props {
  current: RegionMeta;
  onSelect: (region: RegionMeta) => void;
  onReset: () => void;
  onPoint?: (point: ClickedLocation) => void;
}

type PointFC = GeoJSON.FeatureCollection<GeoJSON.Point, { id: string; name: string; level: RegionLevel; selected: boolean }>;
const EMPTY: RegionFeatureCollection = { type: "FeatureCollection", features: [] };
const EMPTY_POINTS: PointFC = { type: "FeatureCollection", features: [] };

const NAVY = "#03363D";
const SELECT = "#03363D";
const SELECT_FILL = "#BDD9D7";
const childOf: Record<RegionLevel, RegionLevel | undefined> = { country: "state", state: "district", district: "block", block: "panchayat", panchayat: undefined };
const lineWidth: Record<RegionLevel, number> = { country: 1.4, state: 1.1, district: 0.8, block: 0.6, panchayat: 0.5 };

type LayerKey = "admin" | "state" | "district" | "block" | "panchayat";
const LAYER_LABELS: [LayerKey, string][] = [
  ["admin", "Administrative boundaries"],
  ["state", "State boundaries"],
  ["district", "District boundaries"],
  ["block", "Block boundaries / locations"],
  ["panchayat", "Panchayat boundaries / locations"],
];
const DEFAULT_LAYERS: Record<LayerKey, boolean> = { admin: true, state: true, district: true, block: true, panchayat: true };

const OWN_SOURCES = ["children", "focus", "points", "focus-point", "india", "context", "focus-label"];
const validBounds = (b?: Bounds): b is Bounds => Boolean(b && b.flat().every(Number.isFinite) && b[0][0] <= b[1][0] && b[0][1] <= b[1][1] && !(b[0][0] === 0 && b[0][1] === 0));
const log = (...a: unknown[]) => {
  if (import.meta.env.DEV) console.info(...a);
};

export function MonsoonMap({ current, onSelect, onReset, onPoint }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const selectRef = useRef(onSelect);
  const pointRef = useRef(onPoint);
  const dataRef = useRef<{ children: RegionFeatureCollection; focus: RegionFeatureCollection; context: RegionFeatureCollection; label: PointFC; points: PointFC; focusPoint: PointFC }>({ children: EMPTY, focus: EMPTY, context: EMPTY, label: EMPTY_POINTS, points: EMPTY_POINTS, focusPoint: EMPTY_POINTS });
  const [instance, setInstance] = useState(0);
  const [layerMenu, setLayerMenu] = useState(false);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [status, setStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [tileWarning, setTileWarning] = useState(false);
  const [dataError, setDataError] = useState<string>();
  const [styleVersion, setStyleVersion] = useState(0);
  const [loadingBoundaries, setLoadingBoundaries] = useState(false);
  const [hover, setHover] = useState<{ x: number; y: number; name: string; level: RegionLevel }>();
  const [dataVersion, setDataVersion] = useState(geographyService.getVersion());

  selectRef.current = onSelect;
  pointRef.current = onPoint;

  useEffect(() => geographyService.subscribe(() => setDataVersion(geographyService.getVersion())), []);

  useEffect(() => {
    log("[Map] container mounted");
  }, []);

  const pushData = useCallback((map: MlMap) => {
    const d = dataRef.current;
    (map.getSource("children") as GeoJSONSource | undefined)?.setData(d.children);
    (map.getSource("focus") as GeoJSONSource | undefined)?.setData(d.focus);
    (map.getSource("points") as GeoJSONSource | undefined)?.setData(d.points);
    (map.getSource("focus-point") as GeoJSONSource | undefined)?.setData(d.focusPoint);
    (map.getSource("context") as GeoJSONSource | undefined)?.setData(d.context);
    (map.getSource("focus-label") as GeoJSONSource | undefined)?.setData(d.label);
  }, []);

  // ---- Map lifecycle: exactly one instance per container; torn down on unmount/retry. ----
  useEffect(() => {
    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let observer: ResizeObserver | undefined;
    let usedFallback = false;
    let tileErrors = 0;
    let basemapSourceLogged = false;
    let clickSeq = 0;
    setStatus("loading");
    setTileWarning(false);

    log("[Map] initializing");
    log("[Map] style loading");
    void import("maplibre-gl")
      .then((maplibregl) => {
        const container = containerRef.current;
        if (cancelled || !container || mapRef.current) return;
        const map = new maplibregl.Map({
          container,
          style: MAP_STYLE_URL,
          bounds: INDIA_BOUNDS,
          fitBoundsOptions: { padding: 24 },
          maxBounds: MAX_BOUNDS,
          minZoom: MIN_ZOOM,
          attributionControl: false,
        });
        mapRef.current = map;
        log("[Map] instance created");
        if (import.meta.env.DEV) (window as unknown as { __monsoonMap?: MlMap }).__monsoonMap = map;
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new maplibregl.FullscreenControl(), "top-right");
        map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: GEO_ATTRIBUTION }), "bottom-right");

        const useFallback = () => {
          if (usedFallback || cancelled) return;
          usedFallback = true;
          log("[Map] Primary style unavailable, switching to fallback basemap");
          setTileWarning(true);
          map.setStyle(FALLBACK_STYLE);
        };
        timeout = setTimeout(() => {
          if (!map.isStyleLoaded()) useFallback();
        }, STYLE_TIMEOUT_MS);

        map.on("error", (event) => {
          const sourceId = (event as { sourceId?: string }).sourceId;
          if (!map.isStyleLoaded() && !sourceId) {
            if (!usedFallback) useFallback();
            else setStatus("failed");
            return;
          }
          if (sourceId && !OWN_SOURCES.includes(sourceId)) {
            tileErrors += 1;
            if (import.meta.env.DEV) console.error("[Map ERROR] Basemap tile error", event.error);
            if (tileErrors > 4 && !usedFallback) useFallback();
            else if (tileErrors > 8 && usedFallback) setStatus("failed");
            else if (tileErrors > 4) setTileWarning(true);
          }
        });

        map.on("sourcedata", (event) => {
          if (!basemapSourceLogged && event.isSourceLoaded && event.sourceId && !OWN_SOURCES.includes(event.sourceId)) {
            basemapSourceLogged = true;
            log("[Map] basemap source loaded:", event.sourceId);
            log("[Map] sources loaded");
          }
        });

        map.on("style.load", () => {
          if (cancelled) return;
          clearTimeout(timeout);
          log("[Map] Style loaded");
          installLayers(map);
          log("[Map] layers added");
          pushData(map);
          container.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
          setStatus("ready");
          setStyleVersion((v) => v + 1);
          map.resize();
          log("[Map] map ready");
          map.once("idle", () => log("[Map] geographic features rendered"));
        });

        map.on("mousemove", (event) => {
          const hit = map.queryRenderedFeatures(event.point, { layers: ["children-hit", "points-circle"].filter((id) => map.getLayer(id)) })[0];
          const id = hit?.properties?.["id"];
          if (map.getLayer("children-hover")) map.setFilter("children-hover", ["==", ["get", "id"], typeof id === "string" ? id : ""]);
          map.getCanvas().style.cursor = hit ? "pointer" : "";
          setHover(hit && typeof id === "string" ? { x: event.point.x, y: event.point.y, name: String(hit.properties["name"]), level: hit.properties["level"] as RegionLevel } : undefined);
        });
        map.on("mouseout", () => setHover(undefined));


        map.on("click", (event: MapLayerMouseEvent) => {
          const longitude = event.lngLat.lng;
          const latitude = event.lngLat.lat;
          setHover(undefined);
          // Location-point-only records (no polygon exists) are selected by clicking their marker.
          const hit = map.queryRenderedFeatures(event.point, { layers: ["points-circle"].filter((id) => map.getLayer(id)) })[0];
          const pointRegion = typeof hit?.properties?.["id"] === "string" ? geographyService.getRegion(hit.properties["id"]) : undefined;
          if (pointRegion) {
            pointRef.current?.({ longitude, latitude, detected: { chain: geographyService.getAncestors(pointRegion).slice(1), region: pointRegion, blockMissing: false } });
            selectRef.current(pointRegion);
            return;
          }
          pointRef.current?.({ longitude, latitude });
          const clickId = ++clickSeq;
          void geographyService
            .detectAt(longitude, latitude)
            .then((detected) => {
              if (cancelled || clickId !== clickSeq) return;
              pointRef.current?.({ longitude, latitude, detected });
              if (detected.region) selectRef.current(detected.region);
            })
            .catch((cause: unknown) => {
              if (import.meta.env.DEV) console.error("[MonsoonScope Click] detection failed", cause);
              pointRef.current?.({ longitude, latitude, detected: { chain: [], blockMissing: false } });
            });
        });

        observer = new ResizeObserver(() => map.resize());
        observer.observe(container);
      })
      .catch((cause: unknown) => {
        if (import.meta.env.DEV) console.error("[Map ERROR] Initialization failed", cause);
        setStatus("failed");
      });

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      observer?.disconnect();
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [instance, pushData]);

  // ---- Data for the current selection (progressive disclosure + camera). ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    let cancelled = false;
    setLoadingBoundaries(true);
    const parent = geographyService.getParent(current);
    // At a leaf-ish point level, show siblings so neighbouring locations stay clickable.
    const pointHost = current.geometryStatus === "point" && parent ? parent : current;
    const toPoint = (r: RegionMeta) => r.center ? ({ type: "Feature" as const, geometry: { type: "Point" as const, coordinates: r.center }, properties: { id: r.id, name: r.name, level: r.level, selected: r.id === current.id } }) : undefined;

    const contextRegion = current.level === "block" || current.level === "panchayat" ? geographyService.getAncestors(current).find((r) => r.level === "district") : undefined;
    void Promise.all([geographyService.getChildPolygons(current), geographyService.getGeometry(current), contextRegion ? geographyService.getGeometry(contextRegion) : undefined])
      .then(([kids, ownFocus, context]) => {
        if (cancelled) return;
        // Panchayat without polygon: keep the parent block boundary as the highlighted area.
        let focus = ownFocus;
        if (!focus && current.level === "panchayat") {
          const block = geographyService.getParent(current);
          if (block?.geometry && block.geometry.type === "Feature") focus = block.geometry;
        }
        const anchor = focus ? geographyService.labelPoint(focus) : undefined;
        const labelled = ownFocus ? current : focus ? geographyService.getParent(current) : undefined;
        dataRef.current = {
          children: kids,
          focus: focus ? { type: "FeatureCollection", features: [focus] } : EMPTY,
          context: context ? { type: "FeatureCollection", features: [context] } : EMPTY,
          label: anchor && labelled ? { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: anchor }, properties: { id: labelled.id, name: labelled.name.toUpperCase(), level: labelled.level, selected: true } }] } : EMPTY_POINTS,
          points: { type: "FeatureCollection", features: geographyService.getChildPoints(pointHost).map(toPoint).filter((feature): feature is NonNullable<typeof feature> => Boolean(feature)) },
          focusPoint: current.geometryStatus === "point" && current.center ? { type: "FeatureCollection", features: [toPoint(current)].filter((feature): feature is NonNullable<typeof feature> => Boolean(feature)) } : EMPTY_POINTS,
        };
        pushData(map);
        log("[Map] Administrative layers loaded:", current.name);
        if (current.level === "state") log("[Map] district geometry loaded:", kids.features.length);
        if (current.level === "district") log("[Map] block data loaded:", dataRef.current.points.features.length);
        if (current.level === "block") log("[Map] panchayat metadata loaded:", geographyService.getPanchayats(current.id).length);
        setDataError(undefined);
      })
      .catch((cause: unknown) => {
        if (!cancelled) {
          if (import.meta.env.DEV) console.error("[Map ERROR] Geography failed", cause);
          setDataError(cause instanceof Error ? cause.message : "Boundary data failed to load");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingBoundaries(false);
      });
    return () => {
      cancelled = true;
    };
  }, [current, status, styleVersion, dataVersion, pushData]);

  // Camera — deterministic, validated.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900;
    if (current.geometryStatus === "point" && current.center && (current.level === "block" || current.level === "panchayat")) {
      const [lon, lat] = current.center;
      if (Number.isFinite(lon) && Number.isFinite(lat)) map.flyTo({ center: [lon, lat], zoom: POINT_ZOOM[current.level], duration });
    } else if (validBounds(current.bounds)) {
      map.fitBounds(current.bounds, { padding: 50, duration, maxZoom: 13 });
    } else {
      let parent = geographyService.getParent(current);
      while (parent && !parent.center && !validBounds(parent.bounds)) parent = geographyService.getParent(parent);
      if (parent?.geometryStatus === "point" && parent.center) map.flyTo({ center: parent.center, zoom: parent.level === "block" ? POINT_ZOOM.block : 10, duration });
      else if (validBounds(parent?.bounds)) map.fitBounds(parent.bounds, { padding: 50, duration, maxZoom: 13 });
    }
  }, [current, status]);

  // Layer visibility — selected geometry (focus) is never hidden.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const childLevel = childOf[current.level];
    const vis = (on: boolean) => (on ? "visible" : "none");
    const childOn = layers.admin && (childLevel ? layers[childLevel as LayerKey] : false);
    if (map.getLayer("india-outline")) map.setLayoutProperty("india-outline", "visibility", vis(layers.admin));
    for (const id of ["children-outline", "children-hover"]) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(childOn));
    if (map.getLayer("children-outline") && childLevel) map.setPaintProperty("children-outline", "line-width", lineWidth[childLevel]);
    const pointsOn = layers.admin && (current.level === "district" || current.level === "block" ? layers.block : layers.panchayat);
    for (const id of ["points-circle", "points-label"]) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis(pointsOn));
  }, [layers, current, status, styleVersion]);

  const hasPoints = current.level === "district" || current.level === "block" || current.level === "panchayat";
  const noPanchayatData = current.level === "block" && geographyService.getPanchayats(current.id).length === 0;

  return (
    <div className="map-stage relative w-full overflow-hidden bg-map" data-map-root>
      <div ref={containerRef} key={instance} style={{ position: "absolute", inset: 0 }} aria-label={`Interactive map centered on ${current.name}`} />

      <div className="absolute left-3 top-3 z-10 max-w-[72%] rounded-md border border-border bg-card/95 px-3 py-2 shadow-sm backdrop-blur-[2px]">
        <p className="text-[9px] font-bold uppercase text-muted-foreground">Current geographic context · {LEVEL_LABEL[current.level]}</p>
        <p className="text-sm font-semibold text-foreground">{current.name}</p>
        <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
          {current.geometryStatus === "boundary" ? "Boundary geometry" : current.geometryStatus === "point" && current.center ? `Location point only · ${current.center[1].toFixed(4)}°N ${current.center[0].toFixed(4)}°E` : "Metadata only · location geometry unavailable"}
        </p>
        {current.attributes && (
          <p className="mt-0.5 text-[10px] text-muted-foreground">
            {current.attributes.elevationM} m · slope {current.attributes.slopeDeg}°{current.attributes.landcoverName ? ` · ${current.attributes.landcoverName}` : ` · landcover class ${current.attributes.landcoverClass}`}
          </p>
        )}
        {current.level === "panchayat" && current.geometryStatus !== "boundary" && <p className="mt-1 rounded-sm bg-muted px-2 py-1 text-[10px] font-semibold text-muted-foreground">Panchayat geometry · Not available</p>}
        {noPanchayatData && <p className="mt-1 text-[10px] font-semibold text-watch">No Panchayat dataset available for this block</p>}
        {(status === "loading" || loadingBoundaries) && <p className="mt-1 text-[10px] text-muted-foreground">{status === "loading" ? "Loading geographic layers…" : "Loading administrative boundaries…"}</p>}
      </div>

      {tileWarning && status !== "failed" && (
        <div className="absolute inset-x-3 bottom-24 z-20 mx-auto max-w-md rounded-md border border-border bg-card px-3 py-2 text-xs text-muted-foreground shadow-sm">
          Map tiles are temporarily unavailable. Geographic selection is still available from the selectors.
        </div>
      )}
      {dataError && <div className="absolute inset-x-3 top-28 z-20 border border-destructive bg-background p-2 text-xs text-destructive">{dataError}</div>}
      {status === "failed" && (
        <div className="absolute inset-0 z-30 grid place-items-center bg-map">
          <div className="rounded-md border border-border bg-card p-4 text-center shadow-sm">
            <p className="metric-label">Data unavailable</p><p className="mt-1 text-sm font-semibold">Map tiles unavailable</p>
            <p className="mt-1 text-xs text-muted-foreground">Try refreshing the map. Selectors above still work.</p>
            <Button size="sm" variant="outline" className="mt-3" onClick={() => setInstance((v) => v + 1)}>
              <RotateCw className="mr-1 size-3" /> Retry
            </Button>
          </div>
        </div>
      )}

      {hover && (
        <div className="pointer-events-none absolute z-20 rounded-sm border border-border bg-card px-2.5 py-1.5 text-xs shadow-sm" style={{ left: Math.min(hover.x + 12, (containerRef.current?.clientWidth ?? 400) - 160), top: Math.max(hover.y - 36, 4) }}>
          <p className="font-semibold">{hover.name}</p>
          <p className="text-[10px] text-muted-foreground">{LEVEL_LABEL[hover.level]}</p>
        </div>
      )}

      <div className="absolute right-12 top-3 z-10 flex gap-1.5">
        <Button size="icon" aria-label="Layer controls" title="Layer controls" className="shadow-sm" onClick={() => setLayerMenu((v) => !v)}>
          <Layers3 className="size-4" />
        </Button>
        <Button
          size="icon"
          className="shadow-sm"
          aria-label="Reset map to India"
          title="Reset to India"
          onClick={() => {
            setLayers(DEFAULT_LAYERS);
            setHover(undefined);
            onReset();
          }}
        >
          <LocateFixed className="size-4" />
        </Button>
      </div>
      {layerMenu && (
        <div className="absolute right-3 top-14 z-20 w-64 rounded-md border border-border bg-card p-3 shadow-md">
          <p className="metric-label mb-2">Administrative layers</p>
          {LAYER_LABELS.map(([key, label]) => (
            <label className="mt-2 flex items-center justify-between gap-3 text-sm" key={key}>
              <span className={key !== "admin" ? "pl-3 text-muted-foreground" : ""}>{label}</span>
              <input className="accent-primary" type="checkbox" checked={layers[key]} onChange={(e) => setLayers((prev) => ({ ...prev, [key]: e.target.checked }))} />
            </label>
          ))}
          <p className="mt-3 text-[10px] text-muted-foreground">The selected area always stays visible.</p>
          <button className="mt-2 text-xs font-medium text-primary hover:underline" onClick={() => setLayerMenu(false)}>
            Close
          </button>
        </div>
      )}

      <div className="absolute bottom-7 left-3 z-10 rounded-md border border-border bg-card/95 p-2.5 text-[10px] shadow-sm backdrop-blur-[2px]">
        <p className="mb-1.5 font-bold uppercase text-muted-foreground">Legend</p>
        <p className="flex items-center gap-2"><span className="h-0 w-5 border-t-2" style={{ borderColor: SELECT }} />Selected area</p>
        <p className="mt-1 flex items-center gap-2"><span className="h-0 w-5 border-t" style={{ borderColor: NAVY }} />{current.level === "country" ? "State boundary" : current.level === "state" ? "District boundary" : current.level === "district" || current.level === "block" || current.level === "panchayat" ? "Block boundary" : "Administrative boundary"}</p>
        {hasPoints && current.level === "district" && geographyService.getChildPoints(current).length > 0 && <p className="mt-1 flex items-center gap-2"><span className="size-2.5 rounded-full border border-background" style={{ backgroundColor: NAVY }} />Block location</p>}
        {hasPoints && current.level !== "district" && geographyService.getChildPoints(current).length > 0 && <p className="mt-1 flex items-center gap-2"><span className="size-2.5 rounded-full border border-background" style={{ backgroundColor: NAVY }} />Panchayat location</p>}
        {current.geometryStatus === "point" && <p className="mt-1 flex items-center gap-2"><span className="size-2.5 rounded-full border-2" style={{ borderColor: SELECT }} />Selected location</p>}
      </div>
    </div>
  );
}

function installLayers(map: MlMap) {
  if (map.getSource("children")) return;
  map.addSource("india", { type: "geojson", data: EMPTY });
  void geographyService
    .getIndiaOutline()
    .then((india) => {
      (map.getSource("india") as GeoJSONSource | undefined)?.setData(india);
      log("[Map] state geometry loaded");
    })
    .catch((cause: unknown) => {
      if (import.meta.env.DEV) console.error("[Map ERROR] India geometry failed", cause);
    });
  map.addSource("children", { type: "geojson", data: EMPTY });
  map.addSource("focus", { type: "geojson", data: EMPTY });
  map.addSource("points", { type: "geojson", data: EMPTY_POINTS });
  map.addSource("focus-point", { type: "geojson", data: EMPTY_POINTS });
  map.addSource("context", { type: "geojson", data: EMPTY });
  map.addSource("focus-label", { type: "geojson", data: EMPTY_POINTS });
  map.addLayer({ id: "context-outline", type: "line", source: "context", paint: { "line-color": NAVY, "line-width": 1, "line-opacity": 0.45 } });

  map.addLayer({ id: "children-hit", type: "fill", source: "children", paint: { "fill-color": NAVY, "fill-opacity": 0 } });
  map.addLayer({ id: "children-outline", type: "line", source: "children", paint: { "line-color": "#607477", "line-width": 0.8, "line-opacity": 0.72 } });
  map.addLayer({ id: "children-hover", type: "line", source: "children", paint: { "line-color": NAVY, "line-width": 1.8 }, filter: ["==", ["get", "id"], ""] });
  map.addLayer({ id: "india-outline", type: "line", source: "india", paint: { "line-color": NAVY, "line-width": 1.3 } });
  map.addLayer({ id: "focus-fill", type: "fill", source: "focus", paint: { "fill-color": SELECT_FILL, "fill-opacity": 0.22 } });
  map.addLayer({ id: "focus-outline", type: "line", source: "focus", paint: { "line-color": SELECT, "line-width": 2.7 } });
  map.addLayer({
    id: "points-circle",
    type: "circle",
    source: "points",
    paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 3, 12, 6], "circle-color": NAVY, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.2, "circle-opacity": ["case", ["get", "selected"], 0, 0.85] },
  });
  map.addLayer({
    id: "points-label",
    type: "symbol",
    source: "points",
    minzoom: 8,
    layout: { "text-field": ["get", "name"], "text-font": LABEL_FONT, "text-size": 11, "text-offset": [0, 1.1], "text-anchor": "top", "text-optional": true },
    paint: { "text-color": NAVY, "text-halo-color": "#ffffff", "text-halo-width": 1.4 },
  });
  map.addLayer({
    id: "focus-label",
    type: "symbol",
    source: "focus-label",
    layout: { "text-field": ["get", "name"], "text-font": LABEL_FONT, "text-size": 13, "text-letter-spacing": 0.08, "text-allow-overlap": true },
    paint: { "text-color": SELECT, "text-halo-color": "#ffffff", "text-halo-width": 1.8 },
  });
  map.addLayer({ id: "focus-point", type: "circle", source: "focus-point", paint: { "circle-radius": 8, "circle-color": "#ffffff", "circle-stroke-color": SELECT, "circle-stroke-width": 3 } });
  map.addLayer({
    id: "focus-point-label",
    type: "symbol",
    source: "focus-point",
    layout: { "text-field": ["get", "name"], "text-font": LABEL_FONT, "text-size": 12, "text-offset": [0, 1.3], "text-anchor": "top" },
    paint: { "text-color": SELECT, "text-halo-color": "#ffffff", "text-halo-width": 1.6 },
  });
}
