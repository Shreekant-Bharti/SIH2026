"""Build public/geo/blocks.json from data-sources/India_Block_Master_Metadata.csv.

Blocks are LOCATION POINTS (lat/lon) — no boundary geometry is created.
Each block is attached to a geoBoundaries district id: by normalized name within
its state first, otherwise by the district polygon containing the majority of
that source district's block points. Source codes/names are preserved.
"""
import difflib, csv, json, re, unicodedata, collections, os
from shapely.geometry import shape, Point
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^the ", "", s); s = s.replace("&", "and")
    return re.sub(r"[^a-z]", "", s)
rows = list(csv.DictReader(open(f"{ROOT}/data-sources/India_Block_Master_Metadata.csv")))
states = {norm(f["properties"]["name"]): f["properties"]["id"] for f in json.load(open(f"{ROOT}/public/geo/states.json"))["features"]}
dist_polys = {}
for sid in set(states.values()):
    p = f"{ROOT}/public/geo/districts/{sid}.json"
    if os.path.exists(p):
        dist_polys[sid] = [(f["properties"]["id"], norm(f["properties"]["name"]), shape(f["geometry"])) for f in json.load(open(p))["features"]]
groups = collections.defaultdict(list)
for r in rows: groups[(r["STATE_CODE"], r["DISTRICT_CODE"])].append(r)
lc = {}; out = []; unmatched = []; method = collections.Counter()
for (sc, dc), rs in groups.items():
    sid = states.get(norm(rs[0]["STATE_NAME"]))
    polys = dist_polys.get(sid, [])
    did = next((i for i, n, _ in polys if n == norm(rs[0]["DISTRICT_NAME"])), None)
    if did: method["name"] += 1
    else:
        votes = collections.Counter()
        for r in rs:
            pt = Point(float(r["LONGITUDE"]), float(r["LATITUDE"]))
            for i, _, g in polys:
                if g.contains(pt): votes[i] += 1; break
        if votes: did = votes.most_common(1)[0][0]; method["point"] += 1
    if not did and polys:
        best = max(polys, key=lambda t: difflib.SequenceMatcher(None, t[1], norm(rs[0]["DISTRICT_NAME"])).ratio())
        pt = Point(float(rs[0]["LONGITUDE"]), float(rs[0]["LATITUDE"]))
        near = min(polys, key=lambda t: t[2].distance(pt))
        did = best[0] if difflib.SequenceMatcher(None, best[1], norm(rs[0]["DISTRICT_NAME"])).ratio() > 0.6 else near[0]
        method["fuzzy/nearest"] += 1
    if not did: unmatched.append(f'{rs[0]["STATE_NAME"]}/{rs[0]["DISTRICT_NAME"]}'); continue
    for r in rs:
        lat, lon = float(r["LATITUDE"]), float(r["LONGITUDE"])
        if not (5 < lat < 38 and 67 < lon < 98): continue
        lc[r["LANDCOVER_CLASS"]] = r["LANDCOVER_NAME"]
        out.append([f"blk-{sc}-{dc}-{r['BLOCK_CODE']}", r["BLOCK_NAME"], did, f"{sc}-{dc}-{r['BLOCK_CODE']}",
                    r["STATE_NAME"], r["DISTRICT_NAME"], round(lon,4), round(lat,4), float(r["ELEVATION_M"]), float(r["SLOPE_DEG"]), int(r["LANDCOVER_CLASS"])])
json.dump({"source": "India_Block_Master_Metadata.csv", "fields": ["id","name","districtId","code","sourceState","sourceDistrict","lon","lat","elevationM","slopeDeg","landcoverClass"],
           "landcover": {int(k): v for k, v in lc.items()}, "blocks": out}, open(f"{ROOT}/public/geo/blocks.json", "w"), separators=(",", ":"))
print(len(out), "blocks", dict(method), "unmatched districts:", len(unmatched), unmatched[:20])
