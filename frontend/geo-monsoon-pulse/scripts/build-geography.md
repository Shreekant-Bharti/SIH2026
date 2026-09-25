# Administrative geography data

The app never ships invented administrative data. Everything under
`public/geo/` and `src/data/geography/generated/` is produced from an
authoritative source by the pipeline below.

## Current sources

| Level | Source | Licence | Status |
| --- | --- | --- | --- |
| Country (ADM0) | geoBoundaries gbOpen IND | CC BY 2.5 IN (DataMeet / ECI) | official |
| State / UT (ADM1), 36 units | geoBoundaries gbOpen IND | CC BY 2.5 IN | official |
| District (ADM2), 735 units | geoBoundaries gbOpen IND | CC BY 2.5 IN | official |
| Block / Tehsil | India Block Master Metadata | supplied project data | 7,233 location points; no polygons |
| Panchayat | Panchayat Master Metadata | supplied project data | 239 Dhanbad metadata records; no coordinates or polygons |

Block and Panchayat boundaries are not bundled. Blocks use source coordinates
as location points. Dhanbad Panchayats use GPCODE as their immutable identity
and remain selectable metadata-only records. The app does not generate or
display polygons, points, circles, or estimated positions for Panchayats.

## Regenerating state / district data

```bash
mkdir -p /tmp/geo && cd /tmp/geo
for L in ADM0 ADM1 ADM2; do
  url=$(curl -s "https://www.geoboundaries.org/api/current/gbOpen/IND/$L/" | python3 -c "import json,sys;print(json.load(sys.stdin)['gjDownloadURL'])")
  curl -sL "$url" -o $L.geojson
done
bunx mapshaper ADM0.geojson -simplify 25% keep-shapes -o precision=0.0001 india_s.geojson
bunx mapshaper ADM1.geojson -simplify 3%  keep-shapes -o precision=0.0001 states_s.geojson
bunx mapshaper ADM2.geojson -simplify 2%  keep-shapes -o precision=0.0001 districts_s.geojson
python3 scripts/prepare-geography.py   # writes public/geo/** and src/data/geography/generated/**
```

## Adding real block / panchayat geometry

1. Export block and panchayat boundaries (LGD codes + Survey of India / Bhuvan
   or a state remote-sensing centre) as GeoJSON.
2. Write one file per parent so loading stays progressive:
   - `public/geo/blocks/<districtId>.json`
   - `public/geo/panchayats/<blockId>.json`
   Feature properties must be `{ id, name, level, parentId }`, with ids shaped
   `<districtId>/<block-slug>` and `<blockId>/<panchayat-slug>`.
3. Register the file in `public/geo/panchayats/manifest.json` under
   `geometryDatasets`. Runtime joins use stable codes, not display names.

No UI or hook changes are required; the geography service is the only seam.

## Blocks (India Block Master Metadata)
`python3 scripts/prepare-blocks.py` reads `data-sources/India_Block_Master_Metadata.csv` (7,233 blocks) and writes
`public/geo/blocks.json`. Blocks are **location points only** — no polygons are generated. IDs are
`blk-<STATE_CODE>-<DISTRICT_CODE>-<BLOCK_CODE>`; elevation, slope and landcover are preserved.

## Panchayats
`scripts/prepare-panchayats.py <csv>` validates and normalizes metadata into
`public/geo/panchayats/dhanbad-metadata.json`. It creates no geometry.

To add geometry, add a GeoJSON file to `public/geo/panchayats/` (Polygon/MultiPolygon or Point features) and list it in
`public/geo/panchayats/manifest.json`:
`{"geometryDatasets":[{"file":"dhanbad.json","blockIdProperty":"blockId","idProperty":"code","nameProperty":"name","source":"..."}]}`
`blockIdProperty` must hold the block id above (e.g. `blk-20-325-3097`). No code changes are needed.
