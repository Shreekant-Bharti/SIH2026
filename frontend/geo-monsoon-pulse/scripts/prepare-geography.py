import json, os, re, math, collections, unicodedata

OUT_PUB = "/dev-server/public/geo"
OUT_SRC = "/dev-server/src/data/geography/generated"
os.makedirs(OUT_PUB + "/districts", exist_ok=True)
os.makedirs(OUT_SRC, exist_ok=True)

def norm(n):
    n = unicodedata.normalize("NFKD", n)
    return "".join(c for c in n if not unicodedata.combining(c)).strip()

def slug(n):
    s = re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
    return s

def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [p[0] for p in geom["coordinates"]]

def bbox(geom):
    xs, ys = [], []
    for r in rings(geom):
        for x, y in r:
            xs.append(x); ys.append(y)
    return [[min(xs), min(ys)], [max(xs), max(ys)]]

def area_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]; x1, y1 = ring[i + 1]
        cr = x0 * y1 - x1 * y0
        a += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    if a == 0:
        return ring[0][0], ring[0][1], 0.0
    a *= 0.5
    return cx / (6 * a), cy / (6 * a), abs(a)

def centroid(geom):
    best = max(rings(geom), key=lambda r: area_centroid(r)[2])
    x, y, _ = area_centroid(best)
    return [round(x, 5), round(y, 5)]

def inside(pt, geom):
    x, y = pt
    for ring in rings(geom):
        c = False
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]; xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
                c = not c
            j = i
        if c:
            return True
    return False

states = json.load(open("/tmp/geo/states_s.geojson"))["features"]
districts = json.load(open("/tmp/geo/districts_s.geojson"))["features"]
india = json.load(open("/tmp/geo/india_s.geojson"))

state_meta = []
for f in states:
    name = norm(f["properties"]["shapeName"])
    sid = slug(name)
    f["properties"] = {"id": sid, "name": name, "level": "state", "parentId": "india", "iso": f["properties"].get("shapeISO") or None}
    f["id"] = sid
    state_meta.append({"id": sid, "name": name, "code": f["properties"].get("iso") or sid, "level": "state", "parentId": "india",
                       "bounds": [[round(v, 5) for v in p] for p in bbox(f["geometry"])],
                       "center": centroid(f["geometry"])})

by_state = collections.defaultdict(list)
dist_meta = []
used = set()
for f in districts:
    name = norm(f["properties"]["shapeName"])
    c = centroid(f["geometry"])
    parent = None
    for sf, sm in zip(states, state_meta):
        if inside(c, sf["geometry"]):
            parent = sm["id"]; break
    if parent is None:
        parent = min(state_meta, key=lambda s: (s["center"][0] - c[0]) ** 2 + (s["center"][1] - c[1]) ** 2)["id"]
    did = slug(name) + "--" + parent
    n = 2
    while did in used:
        did = slug(name) + "-" + str(n) + "--" + parent; n += 1
    used.add(did)
    f["properties"] = {"id": did, "name": name, "level": "district", "parentId": parent}
    f["id"] = did
    by_state[parent].append(f)
    dist_meta.append({"id": did, "name": name, "code": did, "level": "district", "parentId": parent,
                      "bounds": [[round(v, 5) for v in p] for p in bbox(f["geometry"])],
                      "center": c})

india["features"][0]["properties"] = {"id": "india", "name": "India", "level": "country"}
india["features"][0]["id"] = "india"
json.dump(india, open(OUT_PUB + "/india.json", "w"), separators=(",", ":"))
json.dump({"type": "FeatureCollection", "features": states}, open(OUT_PUB + "/states.json", "w"), separators=(",", ":"))
for sid, feats in by_state.items():
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT_PUB}/districts/{sid}.json", "w"), separators=(",", ":"))

header = ("// GENERATED FILE - do not edit by hand.\n"
          "// Source: geoBoundaries gbOpen IND (DataMeet India community / Election Commission of India),\n"
          "// licensed CC BY 2.5 IN. Regenerate with scripts/build-geography.md instructions.\n"
          'import type { RegionMeta } from "@/types/geography";\n\n')
open(OUT_SRC + "/states.ts", "w").write(header + "export const stateIndex: RegionMeta[] = " + json.dumps(state_meta, separators=(",", ":")) + " as RegionMeta[];\n")
open(OUT_SRC + "/districts.ts", "w").write(header + "export const districtIndex: RegionMeta[] = " + json.dumps(dist_meta, separators=(",", ":")) + " as RegionMeta[];\n")
print("states", len(state_meta), "districts", len(dist_meta), "state files", len(by_state))
print(sorted(s["name"] for s in state_meta))
print([d["name"] for d in dist_meta if d["parentId"] == "jharkhand"])
