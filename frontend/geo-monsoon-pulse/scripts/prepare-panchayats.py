"""Normalize uploaded Dhanbad Panchayat metadata without creating geometry.

Input columns: GPCODE,GPNAME,BLOCK,DISTRICT,ELEVATION,SLOPE,LANDCOVER.
GPCODE is the immutable ID. Block names are used only during this validated
import to resolve the existing source-code block ID; runtime joins use IDs.
"""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data-sources" / "panchayat_master_metadata.csv"
rows = list(csv.DictReader(source.open(encoding="utf-8-sig")))
blocks = json.load((ROOT / "public/geo/blocks.json").open())["blocks"]
dhanbad = {str(row[1]).strip().casefold(): row for row in blocks if str(row[5]).strip().casefold() == "dhanbad"}
if len({row["GPCODE"] for row in rows}) != len(rows):
    raise ValueError("GPCODE values must be unique")
out = []
for row in rows:
    block = dhanbad.get(row["BLOCK"].strip().casefold())
    if not block:
        raise ValueError(f"No Dhanbad block match for {row['BLOCK']}")
    out.append([str(row["GPCODE"]), row["GPNAME"].strip(), block[0], row["BLOCK"].strip(), int(row["ELEVATION"]), float(row["SLOPE"]), int(row["LANDCOVER"])])
target = ROOT / "public/geo/panchayats/dhanbad-metadata.json"
target.parent.mkdir(parents=True, exist_ok=True)
json.dump({"source": source.name, "districtId": "dhanbad--jharkhand", "fields": ["gpCode", "name", "blockId", "sourceBlock", "elevationM", "slopeDeg", "landcoverClass"], "panchayats": out}, target.open("w"), separators=(",", ":"))
print(f"Wrote {len(out)} metadata-only Panchayats")
