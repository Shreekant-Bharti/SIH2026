import { districtIndex as generatedDistrictIndex } from "@/data/geography/generated/districts";
import { stateIndex as generatedStateIndex } from "@/data/geography/generated/states";
import { INDIA_BOUNDS, DEFAULT_CENTER } from "@/config/map-config";
import type { Bounds, RegionFeature, RegionFeatureCollection, RegionLevel, RegionMeta, SearchHit } from "@/types/geography";

/**
 * Single access point for administrative geography.
 *
 * - States / districts: boundary geometry from geoBoundaries gbOpen IND
 *   (DataMeet / ECI, CC BY 2.5 IN) in public/geo/.
 * - Blocks: India_Block_Master_Metadata (7,233 records) in public/geo/blocks.json.
 *   LOCATION POINTS ONLY — no block boundary geometry is created.
 * - Panchayats: registered from public/geo/panchayats/manifest.json when real
 *   datasets are supplied (see scripts/build-geography.md). None ship today.
 *
 * Heavy data loads lazily and once; UI subscribes for updates.
 */

const dev = import.meta.env.DEV;
const log = (...args: unknown[]) => {
  if (dev) console.info(...args);
};

const stateIndex: RegionMeta[] = generatedStateIndex.map((r) => ({ ...r, code: r.code ?? r.id, geometryStatus: "boundary" }));
const districtIndex: RegionMeta[] = generatedDistrictIndex.map((r) => ({ ...r, code: r.code ?? r.id, geometryStatus: "boundary" }));

export const INDIA: RegionMeta = { id: "india", name: "India", code: "IN", level: "country", bounds: INDIA_BOUNDS, center: DEFAULT_CENTER, geometryStatus: "boundary" };

export const GEO_ATTRIBUTION = "State/district boundaries: geoBoundaries gbOpen IND (DataMeet / ECI), CC BY 2.5 IN. Block boundaries: Local Government Directory (LGD) 2024 block polygons, CC0, joined by LGD block code. Blocks without an LGD polygon: metadata coordinates.";

export const LEVEL_LABEL: Record<RegionLevel, string> = { country: "Country", state: "State / UT", district: "District", block: "Block / Tehsil", panchayat: "Gram Panchayat" };

const byId = new Map<string, RegionMeta>();
const children = new Map<string, RegionMeta[]>();
const register = (region: RegionMeta) => {
  const previous = byId.get(region.id);
  byId.set(region.id, region);
  if (region.parentId) {
    const list = children.get(region.parentId) ?? [];
    const existingIndex = list.findIndex((item) => item.id === region.id);
    if (existingIndex >= 0) list[existingIndex] = region;
    else list.push(region);
    children.set(region.parentId, list);
  }
  if (previous?.parentId && previous.parentId !== region.parentId) {
    children.set(previous.parentId, (children.get(previous.parentId) ?? []).filter((item) => item.id !== region.id));
  }
};
[INDIA, ...stateIndex, ...districtIndex].forEach(register);
log("[Geography] States loaded:", stateIndex.length);
log("[Geography] Districts loaded:", districtIndex.length);

const listeners = new Set<() => void>();
let version = 0;
const notify = () => {
  version += 1;
  listeners.forEach((fn) => fn());
};

const isFiniteCoord = (lon: unknown, lat: unknown) => typeof lon === "number" && typeof lat === "number" && Number.isFinite(lon) && Number.isFinite(lat) && !(lon === 0 && lat === 0) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
const pointBounds = (lon: number, lat: number): Bounds => [[lon, lat], [lon, lat]];

// ---------- Blocks (points) ----------
interface BlockFile {
  landcover: Record<string, string>;
  blocks: [string, string, string, string, string, string, number, number, number, number, number][];
}
let blocksPromise: Promise<void> | undefined;
let blocksLoaded = false;

// ---------- Panchayats (optional real datasets) ----------
interface PanchayatManifest {
  metadataDatasets?: { file: string; districtId: string; source: string }[];
  geometryDatasets?: { file: string; blockIdProperty: string; idProperty: string; nameProperty: string; source: string }[];
  /** Backward-compatible geometry manifest key. */
  datasets?: { file: string; blockIdProperty: string; idProperty: string; nameProperty: string; source: string }[];
}
interface PanchayatMetadataFile {
  panchayats: [string, string, string, string, number, number, number][];
}
let panchayatPromise: Promise<void> | undefined;
const panchayatFeatures = new Map<string, RegionFeature>();

// ---------- GeoJSON validation ----------
const validRing = (ring: unknown) => Array.isArray(ring) && ring.length >= 4 && ring.every((p) => Array.isArray(p) && isFiniteCoord(p[0], p[1]));
const validGeometry = (g: { type?: string; coordinates?: unknown } | null | undefined): boolean => {
  if (!g || !Array.isArray(g.coordinates)) return false;
  if (g.type === "Polygon") return g.coordinates.length > 0 && g.coordinates.every(validRing);
  if (g.type === "MultiPolygon") return g.coordinates.length > 0 && g.coordinates.every((poly) => Array.isArray(poly) && poly.every(validRing));
  return false;
};
export function sanitizeCollection(input: unknown, label: string): RegionFeatureCollection {
  const fc = input as { type?: string; features?: unknown[] };
  if (!fc || fc.type !== "FeatureCollection" || !Array.isArray(fc.features)) {
    if (dev) console.warn(`[Geography] ${label}: not a FeatureCollection`);
    return { type: "FeatureCollection", features: [] };
  }
  const seen = new Set<string>();
  const features: RegionFeature[] = [];
  for (const raw of fc.features as RegionFeature[]) {
    const id = raw?.properties?.id;
    if (raw?.type !== "Feature" || typeof id !== "string" || !validGeometry(raw.geometry)) {
      if (dev) console.warn(`[Geography] ${label}: skipped invalid feature`, id);
      continue;
    }
    if (seen.has(id)) continue;
    seen.add(id);
    features.push(raw);
  }
  return { type: "FeatureCollection", features };
}

const cache = new Map<string, Promise<RegionFeatureCollection>>();
const load = (key: string, url: string) => {
  const existing = cache.get(key);
  if (existing) return existing;
  if (dev) console.info("[MonsoonScope Map]", `Loading ${key} geometry...`);
  const promise = fetch(url)
    .then(async (response) => {
      if (!response.ok) throw new Error(`Failed to load ${url} (${response.status})`);
      const fc = sanitizeCollection(await response.json(), key);
      if (dev) {
        if (fc.features.length === 0) console.error("[MonsoonScope Map]", `${key} geometry is empty or invalid`);
        else console.info("[MonsoonScope Map]", `${key} geometry loaded: ${fc.features.length} features`);
      }
      return fc;
    })
    .catch((cause: unknown) => {
      cache.delete(key);
      throw cause;
    });
  cache.set(key, promise);
  return promise;
};
const empty = (): RegionFeatureCollection => ({ type: "FeatureCollection", features: [] });

const featureBounds = (feature: RegionFeature): Bounds => {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  const polys = feature.geometry.type === "Polygon" ? [feature.geometry.coordinates] : feature.geometry.coordinates;
  for (const poly of polys) for (const ring of poly) for (const [x, y] of ring) {
    w = Math.min(w, x!); s = Math.min(s, y!); e = Math.max(e, x!); n = Math.max(n, y!);
  }
  return [[w, s], [e, n]];
};

const mapLog = (...a: unknown[]) => {
  if (dev) console.info("[MonsoonScope Map]", ...a);
};

let blockIndexPromise: Promise<Record<string, number>> | undefined;
const loadBlockIndex = () => {
  blockIndexPromise ??= fetch("/geo/blocks/index.json")
    .then(async (r) => (r.ok ? ((await r.json()) as { districts: Record<string, number> }).districts : {}))
    .catch(() => {
      blockIndexPromise = undefined;
      return {};
    });
  return blockIndexPromise;
};
const upgradedDistricts = new Set<string>();

/** Even-odd ray casting over every ring (outer + holes) of each polygon — exact test. */
const ringHits = (ring: number[][], x: number, y: number) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]!;
    const [xj, yj] = ring[j]!;
    if (yi! > y !== yj! > y && x < ((xj! - xi!) * (y - yi!)) / (yj! - yi!) + xi!) inside = !inside;
  }
  return inside;
};
const bboxCache = new WeakMap<RegionFeature, Bounds>();
export function containsPoint(f: RegionFeature, x: number, y: number): boolean {
  let b = bboxCache.get(f);
  if (!b) bboxCache.set(f, (b = featureBounds(f)));
  if (x < b[0][0] || x > b[1][0] || y < b[0][1] || y > b[1][1]) return false; // pre-filter only
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  return polys.some((poly) => poly.reduce((inside, ring) => (ringHits(ring as number[][], x, y) ? !inside : inside), false));
}

/** Interior label point: midpoint of the widest interior span on a horizontal line through the largest polygon. */
function labelPoint(f: RegionFeature): [number, number] | undefined {
  const props = f.properties as unknown as { labelLon?: number; labelLat?: number };
  if (typeof props.labelLon === "number" && typeof props.labelLat === "number") return [props.labelLon, props.labelLat];
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  let best: number[][][] | undefined;
  let bestArea = -1;
  for (const poly of polys) {
    const ring = poly[0] as number[][];
    let a = 0;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j]![0]! * ring[i]![1]! - ring[i]![0]! * ring[j]![1]!);
    if (Math.abs(a) > bestArea) { bestArea = Math.abs(a); best = poly as number[][][]; }
  }
  if (!best) return undefined;
  const ys = best[0]!.map((p) => p[1]!);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  let out: [number, number] | undefined;
  let widest = -1;
  for (const t of [0.5, 0.4, 0.6, 0.3, 0.7]) {
    const y = minY + (maxY - minY) * t;
    const xs: number[] = [];
    for (const ring of best) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i]!; const [xj, yj] = ring[j]!;
      if (yi! > y !== yj! > y) xs.push(((xj! - xi!) * (y - yi!)) / (yj! - yi!) + xi!);
    }
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) if (xs[k + 1]! - xs[k]! > widest) { widest = xs[k + 1]! - xs[k]!; out = [(xs[k]! + xs[k + 1]!) / 2, y]; }
  }
  return out;
}



export const geographyService = {
  subscribe(fn: () => void) {
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  },
  getVersion: () => version,
  isBlocksLoaded: () => blocksLoaded,

  /** Loads the national block point dataset once (≈7k records). */
  loadBlocks(): Promise<void> {
    blocksPromise ??= fetch("/geo/blocks.json")
      .then(async (response) => {
        if (!response.ok) throw new Error(`Block dataset failed to load (${response.status})`);
        const file = (await response.json()) as BlockFile;
        let count = 0;
        for (const [id, name, districtId, code, srcState, srcDistrict, lon, lat, elevationM, slopeDeg, lc] of file.blocks) {
          if (!byId.has(districtId) || !isFiniteCoord(lon, lat)) continue;
          register({
            id, name, code, level: "block", parentId: districtId, center: [lon, lat], bounds: pointBounds(lon, lat), geometryStatus: "point",
            attributes: { sourceStateName: srcState, sourceDistrictName: srcDistrict, elevationM, slopeDeg, landcoverClass: lc, landcoverName: file.landcover[String(lc)] ?? "Unknown" },
          });
          count += 1;
        }
        for (const list of children.values()) if (list[0]?.level === "block") list.sort((a, b) => a.name.localeCompare(b.name));
        blocksLoaded = true;
        log("[Geography] Blocks loaded:", count);
        notify();
        return geographyService.loadPanchayats();
      })
      .catch((cause: unknown) => {
        blocksPromise = undefined;
        throw cause;
      });
    return blocksPromise;
  },

  /** Registers any real Panchayat datasets listed in public/geo/panchayats/manifest.json. */
  loadPanchayats(): Promise<void> {
    panchayatPromise ??= fetch("/geo/panchayats/manifest.json")
      .then(async (response) => {
        const type = response.headers.get("content-type") ?? "";
        if (!response.ok || !type.includes("json")) {
          log("[Geography] Panchayats loaded: 0 (no dataset supplied)");
          return;
        }
        const manifest = (await response.json()) as PanchayatManifest;
        let count = 0;
        for (const ds of manifest.metadataDatasets ?? []) {
          const metadataResponse = await fetch(`/geo/panchayats/${ds.file}`);
          if (!metadataResponse.ok) throw new Error(`Panchayat metadata failed to load (${metadataResponse.status})`);
          const metadata = (await metadataResponse.json()) as PanchayatMetadataFile;
          for (const [gpCode, name, blockId, sourceBlockName, elevationM, slopeDeg, landcoverClass] of metadata.panchayats ?? []) {
            const block = byId.get(blockId);
            if (!block || block.level !== "block" || !gpCode || !name || byId.has(`gp-${gpCode}`)) continue;
            register({
              id: `gp-${gpCode}`,
              name,
              code: gpCode,
              level: "panchayat",
              parentId: blockId,
              geometryStatus: "unavailable",
              attributes: { sourceBlockName, elevationM, slopeDeg, landcoverClass },
            });
            count += 1;
          }
        }
        for (const ds of [...(manifest.geometryDatasets ?? []), ...(manifest.datasets ?? [])]) {
          const raw = (await (await fetch(`/geo/panchayats/${ds.file}`)).json()) as { features: { type: string; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }[] };
          for (const f of raw.features ?? []) {
            const blockId = String(f.properties[ds.blockIdProperty] ?? "");
            const block = byId.get(blockId);
            const code = String(f.properties[ds.idProperty] ?? "");
            const name = String(f.properties[ds.nameProperty] ?? "");
            if (!block || !code || !name) continue;
            const id = `gp-${code}`;
            const existing = byId.get(id);
            if (f.geometry?.type === "Point") {
              const [lon, lat] = f.geometry.coordinates as number[];
              if (!isFiniteCoord(lon, lat)) continue;
              register({ ...existing, id, name, code, level: "panchayat", parentId: blockId, center: [lon!, lat!], bounds: pointBounds(lon!, lat!), geometryStatus: "point" });
            } else {
              const feature = { type: "Feature", geometry: f.geometry, properties: { id, name, level: "panchayat", parentId: blockId } } as RegionFeature;
              if (!validGeometry(feature.geometry)) continue;
              const bounds = featureBounds(feature);
              panchayatFeatures.set(id, feature);
              register({ ...existing, id, name, code, level: "panchayat", parentId: blockId, bounds, center: [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2], geometryStatus: "boundary", geometry: feature });
            }
            count += 1;
          }
        }
        for (const list of children.values()) if (list[0]?.level === "panchayat") list.sort((a, b) => a.name.localeCompare(b.name) || a.code.localeCompare(b.code));
        log("[Geography] Panchayats loaded:", count);
        notify();
      })
      .catch((cause: unknown) => {
        if (dev) console.error("[Geography] Panchayat load failed", cause);
        panchayatPromise = undefined;
        throw cause;
      });
    return panchayatPromise;
  },

  getRoot: () => INDIA,
  getLocationById: (id?: string) => (id ? byId.get(id) : undefined),
  getRegion: (id?: string) => (id ? byId.get(id) : undefined),
  getStates: () => stateIndex,
  getDistricts: (stateId: string) => (children.get(stateId) ?? []).filter((r) => r.level === "district"),
  getBlocks: (districtId: string) => (children.get(districtId) ?? []).filter((r) => r.level === "block"),
  getPanchayats: (blockId: string) => (children.get(blockId) ?? []).filter((r) => r.level === "panchayat"),
  getChildren: (_level: RegionLevel, id: string) => children.get(id) ?? [],
  getParent: (region: RegionMeta) => (region.parentId ? byId.get(region.parentId) : undefined),

  /** India → … → region, oldest ancestor first. */
  getAncestors(region: RegionMeta): RegionMeta[] {
    const chain: RegionMeta[] = [region];
    let cursor = this.getParent(region);
    while (cursor) {
      chain.unshift(cursor);
      cursor = this.getParent(cursor);
    }
    return chain;
  },

  getBlockLocation: (id: string) => byId.get(id)?.center,
  getPanchayatLocation: (id: string) => byId.get(id)?.center,

  /** Polygon layers loaded on demand. Only levels with real boundaries return features. */
  getStateGeometry: async (id: string) => (await load("states", "/geo/states.json")).features.find((f) => f.properties.id === id),
  getDistrictGeometry: async (id: string) => {
    const region = byId.get(id);
    return region?.parentId ? (await load(`districts:${region.parentId}`, `/geo/districts/${region.parentId}.json`)).features.find((f) => f.properties.id === id) : undefined;
  },
  getBlockGeometry: async (id: string): Promise<RegionFeature | undefined> => {
    const region = byId.get(id);
    if (!region?.parentId) return undefined;
    return (await geographyService.loadBlockBoundaries(region.parentId)).features.find((f) => f.properties.id === id);
  },
  getPanchayatGeometry: async (id: string) => panchayatFeatures.get(id),

  getIndiaOutline: () => load("country", "/geo/india.json"),

  /**
   * Official LGD 2024 community-development block polygons for a district, joined to the
   * block metadata by exact LGD district + block code (no name or proximity matching). Upgrades matching blocks to "boundary".
   */
  async loadBlockBoundaries(districtId: string): Promise<RegionFeatureCollection> {
    const index = await loadBlockIndex();
    if (!index[districtId]) return empty();
    await geographyService.loadBlocks();
    const fc = await load(`blocks:${districtId}`, `/geo/blocks/${districtId}.json`);
    if (!upgradedDistricts.has(districtId)) {
      upgradedDistricts.add(districtId);
      let n = 0;
      for (const f of fc.features) {
        const region = byId.get(f.properties.id);
        if (!region || region.level !== "block" || region.parentId !== districtId) continue;
        register({ ...region, geometryStatus: "boundary", bounds: featureBounds(f), center: labelPoint(f) ?? region.center ?? [(featureBounds(f)[0][0] + featureBounds(f)[1][0]) / 2, (featureBounds(f)[0][1] + featureBounds(f)[1][1]) / 2], geometry: f });
        n += 1;
      }
      mapLog(`Block geometry loaded: ${n} features (${districtId})`);
      notify();
    }
    return fc;
  },

  /** Exact point-in-polygon detection down the hierarchy: state → district → block → panchayat. */
  async detectAt(lon: number, lat: number): Promise<{ chain: RegionMeta[]; region?: RegionMeta; blockMissing: boolean }> {
    const chain: RegionMeta[] = [];
    const clog = (...a: unknown[]) => dev && console.info("[MonsoonScope Click]", ...a);
    clog(`Coordinates: ${lat.toFixed(6)}, ${lon.toFixed(6)}`);
    const states = await load("states", "/geo/states.json");
    const state = states.features.find((f) => containsPoint(f, lon, lat));
    const stateMeta = state && byId.get(state.properties.id);
    if (!stateMeta) {
      clog("No administrative boundary found");
      return { chain, blockMissing: false };
    }
    chain.push(stateMeta);
    clog("State:", stateMeta.name);
    const districts = await load(`districts:${stateMeta.id}`, `/geo/districts/${stateMeta.id}.json`);
    const district = districts.features.find((f) => containsPoint(f, lon, lat));
    const districtMeta = district && byId.get(district.properties.id);
    if (!districtMeta) {
      clog("District not found → falling back to state");
      return { chain, region: stateMeta, blockMissing: false };
    }
    chain.push(districtMeta);
    clog("District:", districtMeta.name);
    const blocks = await geographyService.loadBlockBoundaries(districtMeta.id);
    const block = blocks.features.find((f) => containsPoint(f, lon, lat));
    const blockMeta = block && byId.get(block.properties.id);
    if (!blockMeta) {
      clog("Block not found → falling back to district");
      return { chain, region: districtMeta, blockMissing: true };
    }
    chain.push(blockMeta);
    clog("Block:", blockMeta.name);
    const gp = geographyService.getPanchayats(blockMeta.id).find((p) => {
      const f = panchayatFeatures.get(p.id);
      return f ? containsPoint(f, lon, lat) : false;
    });
    if (gp) {
      chain.push(gp);
      clog("Panchayat:", gp.name, gp.code);
      return { chain, region: gp, blockMissing: false };
    }
    return { chain, region: blockMeta, blockMissing: false };
  },

  async getGeometry(region: RegionMeta): Promise<RegionFeature | undefined> {
    if (region.level === "state") return this.getStateGeometry(region.id);
    if (region.level === "district") return this.getDistrictGeometry(region.id);
    if (region.level === "block") return this.getBlockGeometry(region.id);
    if (region.level === "panchayat") return this.getPanchayatGeometry(region.id);
    return undefined;
  },

  /** Child boundary polygons drawn inside a region (progressive disclosure). */
  async getChildPolygons(region: RegionMeta): Promise<RegionFeatureCollection> {
    if (region.level === "country") return load("states", "/geo/states.json");
    if (region.level === "state") return load(`districts:${region.id}`, `/geo/districts/${region.id}.json`);
    if (region.level === "district") return geographyService.loadBlockBoundaries(region.id);
    const kids = children.get(region.id) ?? [];
    const own = kids.flatMap((k) => (k.geometry && k.geometry.type === "Feature" ? [k.geometry] : []));
    // No Panchayat polygons: keep neighbouring block boundaries as lighter context.
    if (!own.length && region.parentId) {
      const parent = byId.get(region.parentId);
      if (parent?.level === "district") return geographyService.loadBlockBoundaries(parent.id);
    }
    return { type: "FeatureCollection", features: own };
  },

  /** Label anchor inside the polygon (never a random coordinate). */
  labelPoint: (f: RegionFeature) => labelPoint(f),

  /** Child regions that only have location points. */
  getChildPoints: (region: RegionMeta) => (children.get(region.id) ?? []).filter((r) => r.geometryStatus === "point"),

  search(query: string, limit = 10): SearchHit[] {
    const term = query.trim().toLowerCase();
    if (term.length < 2) return [];
    const hits: RegionMeta[] = [];
    for (const region of byId.values()) if (region.level !== "country" && region.name.toLowerCase().includes(term)) hits.push(region);
    const rank = { state: 0, district: 1, block: 2, panchayat: 3, country: 4 };
    return hits
      .sort((a, b) => Number(!a.name.toLowerCase().startsWith(term)) - Number(!b.name.toLowerCase().startsWith(term)) || rank[a.level] - rank[b.level] || a.name.localeCompare(b.name))
      .slice(0, limit)
      .map((region) => ({
        region,
        levelLabel: LEVEL_LABEL[region.level],
        context: geographyService.getAncestors(region).slice(1, -1).reverse().map((r) => r.name).join(", "),
      }));
  },

  boundsOf: (region: RegionMeta): Bounds | undefined => region.bounds,
  empty,
};
