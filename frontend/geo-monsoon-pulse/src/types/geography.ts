import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";

export type RegionLevel = "country" | "state" | "district" | "block" | "panchayat";

/** [[west, south], [east, north]] */
export type Bounds = [[number, number], [number, number]];

/** What geometry quality exists for a region. */
export type GeometryStatus = "boundary" | "point" | "unavailable";

/** Block attributes preserved from India_Block_Master_Metadata. */
export interface BlockAttributes {
  sourceStateName?: string;
  sourceDistrictName?: string;
  sourceBlockName?: string;
  elevationM: number;
  slopeDeg: number;
  landcoverClass: number;
  landcoverName?: string;
}

export interface RegionMeta {
  id: string;
  name: string;
  level: RegionLevel;
  parentId?: string;
  /** Stable administrative/source code used independently of the display name. */
  code: string;
  bounds?: Bounds;
  center?: [number, number];
  geometryStatus: GeometryStatus;
  /** Optional boundary, kept separate from hierarchy metadata for replaceable data sources. */
  geometry?: RegionFeature | RegionFeatureCollection;
  attributes?: BlockAttributes;
}

export interface RegionProperties {
  id: string;
  name: string;
  level: RegionLevel;
  parentId?: string;
  /** Mock or model rainfall value attached at render time (mm / 24 h). */
  rain?: number;
}

export type RegionGeometry = Polygon | MultiPolygon;
export type RegionFeature = Feature<RegionGeometry, RegionProperties>;
export type RegionFeatureCollection = FeatureCollection<RegionGeometry, RegionProperties>;

export interface RegionSelection {
  country: RegionMeta;
  state?: RegionMeta;
  district?: RegionMeta;
  block?: RegionMeta;
  panchayat?: RegionMeta;
}

export interface SearchHit {
  region: RegionMeta;
  /** Level label, e.g. "District". */
  levelLabel: string;
  /** Parent chain, e.g. "Dhanbad, Jharkhand". */
  context: string;
}
