import { useMemo, useState, useSyncExternalStore } from "react";
import { ChevronRight, MapPin, Search, X } from "lucide-react";
import { geographyService } from "@/services/geography-service";
import type { RegionMeta, RegionSelection } from "@/types/geography";

interface Props {
  selection: RegionSelection;
  options: { states: RegionMeta[]; districts: RegionMeta[]; blocks: RegionMeta[]; panchayats: RegionMeta[] };
  onSelect: (region?: RegionMeta) => void;
}

const levels = ["state", "district", "block", "panchayat"] as const;
const labels: Record<(typeof levels)[number], string> = {
  state: "State / UT",
  district: "District",
  block: "Block / Tehsil",
  panchayat: "Panchayat",
};
const placeholders: Record<(typeof levels)[number], string> = {
  state: "Select state or UT",
  district: "Select state first",
  block: "Select district first",
  panchayat: "Select block first",
};

export function LocationControls({ selection, options, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const crumbs = [selection.country, selection.state, selection.district, selection.block, selection.panchayat].filter(Boolean) as RegionMeta[];
  const lists = [options.states, options.districts, options.blocks, options.panchayats];
  const version = useSyncExternalStore(geographyService.subscribe, geographyService.getVersion, () => 0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const hits = useMemo(() => geographyService.search(query), [query, version]);

  return (
    <section className="border-b border-border bg-card px-4 py-3 lg:px-6" aria-label="Geographic selection">
      <div className="mx-auto max-w-[1600px]">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div><p className="metric-label mb-1">Location</p><div className="flex min-w-0 items-center gap-1 overflow-x-auto text-sm" aria-label="Selected location">
          <MapPin className="mr-1 size-4 shrink-0 text-primary" />
          {crumbs.map((region, index) => (
            <span className="flex shrink-0 items-center gap-1" key={region.id}>
              <button
                className={index === crumbs.length - 1 ? "font-semibold text-foreground" : "font-medium text-muted-foreground hover:text-primary"}
                onClick={() => onSelect(region)}
              >
                {region.name}
              </button>
              {index < crumbs.length - 1 && <ChevronRight className="size-3 text-muted-foreground" />}
            </span>
          ))}
        </div></div>
        <div className="relative w-full sm:w-96">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-8 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-ring/20"
            placeholder="Search state, district, block or panchayat…"
            onFocus={() => void geographyService.loadBlocks().catch(() => undefined)}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search locations"
          />
          {query && (
            <button className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground" aria-label="Clear search" onClick={() => setQuery("")}>
              <X className="size-4" />
            </button>
          )}
          {hits.length > 0 && (
            <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-md border border-border bg-card shadow-md">
              {hits.map((hit) => (
                <li key={hit.region.id}>
                  <button
                    className="flex w-full items-baseline justify-between gap-3 border-b border-border/70 px-3 py-2.5 text-left text-sm transition-colors last:border-0 hover:bg-secondary/45"
                    onClick={() => {
                      onSelect(hit.region);
                      setQuery("");
                    }}
                  >
                    <span className="min-w-0">
                      <span className="block font-medium">{hit.region.name}</span>
                      {hit.context && <span className="block truncate text-[11px] text-muted-foreground">{hit.context}</span>}
                    </span>
                    <span className="shrink-0 rounded-sm bg-muted px-1.5 py-0.5 text-[9px] font-bold uppercase text-muted-foreground">{hit.levelLabel}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {levels.map((level, index) => {
          const list = lists[index] ?? [];
          const parentPicked = index === 0 || Boolean(selection[levels[index - 1]!]);
          const disabled = list.length === 0;
          return (
            <label className="grid gap-1" key={level}>
              <span className="flex items-baseline justify-between gap-2 text-[11px] font-bold uppercase text-muted-foreground">
                <span>{labels[level]}</span>
                {list.length > 0 && <span className="font-mono text-[10px] font-medium normal-case">{list.length}</span>}
              </span>
              <select
                aria-label={labels[level]}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-medium text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-ring/20 disabled:bg-muted disabled:text-muted-foreground"
                disabled={disabled}
                value={selection[level]?.id ?? ""}
                onChange={(event) => {
                  const region = list.find((item) => item.id === event.target.value);
                  onSelect(region ?? selection[levels[index - 1] as "state"] ?? undefined);
                }}
              >
                <option value="">{disabled ? (parentPicked ? (level === "block" && !geographyService.isBlocksLoaded() ? "Loading blocks…" : `No ${labels[level].toLowerCase()} data available`) : placeholders[level]) : `Select ${labels[level].toLowerCase()}`}</option>
                {list.map((region) => (
                  <option key={region.id} value={region.id}>
                    {region.name}
                  </option>
                ))}
              </select>
            </label>
          );
        })}
      </div>
      {selection.district && (
        <p className="mt-2 border-l-2 border-secondary pl-2 text-[10px] leading-4 text-muted-foreground">
          State and district boundaries: geoBoundaries / DataMeet (CC BY 2.5 IN). Block boundaries: Local Government Directory (LGD) 2024 block polygons, joined by LGD block code (6,659 of 7,233 blocks, incl. all 10 in Dhanbad); other blocks: metadata coordinates only. Panchayat metadata: project Dhanbad Panchayat Master Dataset — 239 records keyed by GPCODE; no Panchayat boundaries.
        </p>
      )}</div>
    </section>
  );
}
