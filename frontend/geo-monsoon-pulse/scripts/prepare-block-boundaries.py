"""Attach official LGD community-development block polygons to the block master metadata.

Geometry source: Local Government Directory (LGD) block polygons, 2024 snapshot
(7,146 blocks, CC0-1.0), distributed by bharatlas.com / yashveeeeeeer/india-geodata:
  https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/admin/blocks/LGD_Blocks.parquet

Join rule: the block master metadata DISTRICT_CODE / BLOCK_CODE are LGD codes, so a
polygon is attached ONLY on an exact (dist_lgd, block_lgd) code match. No name matching,
no point-in-polygon inference, no nearest-centroid logic. Unmatched blocks stay points.

Prepare input (simplified GeoJSON, ~38 MB):
  duckdb -c "install spatial; load spatial; copy (select block_lgd, dist_lgd, state_lgd, block_name,
    ST_SimplifyPreserveTopology(geometry,0.0008) as geom from 'LGD_Blocks.parquet')
    to '/tmp/lgd_blocks.geojson' with (format gdal, driver 'GeoJSON');"
Usage: python3 scripts/prepare-block-boundaries.py /tmp/lgd_blocks.geojson
Output: public/geo/blocks/<districtId>.json + public/geo/blocks/index.json
"""
import json, sys, os, glob
from collections import defaultdict
from shapely.geometry import shape, mapping

src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/lgd_blocks.geojson"
lgd = json.load(open(src))["features"]
blocks = json.load(open("public/geo/blocks.json"))["blocks"]

# code field in blocks.json = "<STATE_CODE>-<DISTRICT_CODE>-<BLOCK_CODE>" (LGD codes)
by_code = {}
for row in blocks:
    _, dist, blk = row[3].split("-")
    by_code[(int(dist), int(blk))] = row

def rnd(o):
    if isinstance(o[0], (int, float)): return [round(o[0], 5), round(o[1], 5)]
    return [rnd(x) for x in o]

out = defaultdict(list)
seen = set()
unmatched = 0
for f in lgd:
    p = f["properties"]
    key = (int(p["dist_lgd"] or 0), int(p["block_lgd"] or 0))
    row = by_code.get(key)
    if not row or key in seen or not f.get("geometry"):
        unmatched += 1
        continue
    g = shape(f["geometry"])
    if not g.is_valid: g = g.buffer(0)
    if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
        unmatched += 1
        continue
    seen.add(key)
    lp = g.representative_point()
    m = mapping(g)
    out[row[2]].append({"type": "Feature", "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"])},
        "properties": {"id": row[0], "name": row[1], "level": "block", "parentId": row[2], "code": row[3],
                       "blockLgd": key[1], "districtLgd": key[0], "stateLgd": p["state_lgd"], "sourceName": p["block_name"],
                       "labelLon": round(lp.x, 5), "labelLat": round(lp.y, 5)}})

os.makedirs("public/geo/blocks", exist_ok=True)
for old in glob.glob("public/geo/blocks/*.json"): os.remove(old)
for did, feats in out.items():
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"public/geo/blocks/{did}.json", "w"), separators=(",", ":"))
json.dump({"source": "Local Government Directory (LGD) block polygons, 2024 snapshot, CC0-1.0 (via bharatlas)", "join": "exact LGD district+block code",
           "districts": {d: len(f) for d, f in out.items()}}, open("public/geo/blocks/index.json", "w"), separators=(",", ":"))
print("blocks with LGD polygons:", len(seen), "of", len(blocks), "| LGD polygons without a metadata record:", unmatched, "| districts:", len(out))
