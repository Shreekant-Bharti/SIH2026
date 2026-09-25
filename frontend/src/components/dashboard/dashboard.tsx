import { useCallback, useMemo, useState } from "react";
import { ArrowDown, Crosshair, Database, MapPinned } from "lucide-react";
import { AlertsList } from "@/components/alerts/alerts-list";
import { RainfallChart } from "@/components/analytics/rainfall-chart";
import { LocationControls } from "@/components/location/location-controls";
import { MonsoonMap, type ClickedLocation } from "@/components/map/monsoon-map";
import { LEVEL_LABEL } from "@/services/geography-service";
import { PredictionPanel } from "@/components/predictions/prediction-panel";
import { WeatherSummary } from "@/components/weather/weather-summary";
import { ModelInformation } from "@/components/scientific/model-information";
import { useGeographicSelection } from "@/hooks/use-geographic-selection";
import { monsoonService } from "@/services/monsoon-service";

export function Dashboard() {
  const location = useGeographicSelection();
  const current = location.current;
  const [point, setPoint] = useState<ClickedLocation>();
  const onPoint = useCallback((next: ClickedLocation) => setPoint(next), []);
  const data = useMemo(() => monsoonService.getRainfallIntelligence(current), [current]);
  const hierarchy = [location.selection.state, location.selection.district, location.selection.block, location.selection.panchayat].filter(Boolean).map((region) => region?.name).join(" · ") || "India";
  const district = location.selection.district;
  const inDhanbad = district?.id === "dhanbad--jharkhand";
  const heading = location.selection.panchayat ? location.selection.panchayat.name : inDhanbad ? "Dhanbad District" : "Panchayat-Level Rainfall Intelligence";
  const subheading = location.selection.panchayat ? [location.selection.block?.name, "Dhanbad", "Jharkhand"].filter(Boolean).join(", ") : "ML-based rainfall downscaling for localized monsoon monitoring and agro-meteorological decision support.";

  return <main>
    <LocationControls selection={location.selection} options={location.options} onSelect={location.select} />
    <section className="border-b border-border bg-deep-panel px-4 py-4 text-header-foreground lg:px-6" aria-label="Rainfall intelligence summary"><div className="mx-auto grid max-w-[1600px] gap-4 lg:grid-cols-[1.5fr_1fr] lg:items-center">
      <div><p className="text-[10px] font-bold uppercase text-secondary">Panchayat-level rainfall intelligence</p><div className="mt-1 flex items-center gap-2"><MapPinned className="size-4 text-secondary"/><h1 className="text-lg font-bold uppercase">{heading}</h1></div><p className="mt-1 max-w-3xl text-xs leading-5 text-header-foreground/65">{subheading}</p></div>
      <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center border border-header-foreground/15 bg-header-foreground/5 p-3"><FlowStep label="Reference rainfall"/><ArrowDown className="size-3 -rotate-90 text-secondary"/><FlowStep label="Ridge Residual"/><ArrowDown className="size-3 -rotate-90 text-secondary"/><FlowStep label="Panchayat rainfall"/></div>
    </div></section>
    <div className="grid border-b border-border xl:grid-cols-[minmax(0,1fr)_380px]">
      <MonsoonMap current={current} onSelect={location.select} onReset={() => { setPoint(undefined); location.reset(); }} onPoint={onPoint} />
      <aside className="border-t border-border bg-deep-panel text-header-foreground xl:border-l xl:border-t-0">
        <div className="border-b border-header-foreground/15 p-5">
          <div className="flex items-center justify-between gap-3"><p className="text-[10px] font-bold uppercase text-secondary">Area briefing</p><span className="rounded-sm border border-header-foreground/20 px-2 py-1 text-[9px] font-bold uppercase text-header-foreground/60">{LEVEL_LABEL[current.level]}</span></div>
          <h2 className="mt-2 text-2xl font-bold">{current.name}</h2>
          <p className="mt-1 text-xs font-medium text-header-foreground/55">{hierarchy}</p>
           <p className="mt-3 text-sm leading-6 text-header-foreground/70">{current.level === "panchayat" ? "Selected project Panchayat metadata record." : "Geographic location available for administrative exploration."}</p>
           <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-sm bg-header-foreground/15"><Brief label="Geometry status" value={current.level === "panchayat" && current.geometryStatus !== "boundary" ? "Panchayat polygon unavailable" : current.geometryStatus === "boundary" ? "Verified boundary" : current.geometryStatus === "point" ? "Location point" : "Metadata available"}/><Brief label={current.level === "panchayat" ? "GPCODE" : "Administrative code"} value={current.code}/><Brief label="Model coverage" value={data.coverage === "available" ? "Dhanbad District, Jharkhand" : "Unavailable for selected location"}/><Brief label="Model status" value={data.state === "success" ? "Available" : "Data unavailable"}/></div>
        </div>
        <div className="border-b border-header-foreground/15 p-5">
          <div className="flex items-center justify-between gap-3">
            <p className="flex items-center gap-2 text-[10px] font-bold uppercase text-secondary"><Crosshair className="size-3.5" />{point ? "Selected location" : "Map inspection"}</p>
            {point && <button className="text-xs font-semibold text-secondary hover:underline" onClick={() => setPoint(undefined)}>Clear</button>}
          </div>
           {point ? <>
            {!point.detected ? <p className="mt-2 text-sm text-header-foreground/60">Detecting administrative area…</p> : point.detected.region ? <>
              <div className="mt-2 space-y-0.5 text-sm">
                {point.detected.chain.map((r) => <p key={r.id}><span className="inline-block w-24 text-xs text-header-foreground/50">{LEVEL_LABEL[r.level]}</span><span className="font-semibold">{r.name}</span></p>)}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <p className="text-header-foreground/50">Detected level</p><p className="text-right font-semibold">{LEVEL_LABEL[point.detected.region.level]}</p>
                <p className="text-header-foreground/50">Detected area</p><p className="text-right font-semibold">{point.detected.region.name}</p>
              </div>
              {point.detected.blockMissing && <p className="mt-3 rounded-sm border border-header-foreground/15 bg-header-foreground/5 p-2 text-xs text-header-foreground/65"><strong className="block text-secondary">District-level match</strong>No confirmed block boundary covers this point.</p>}
            </> : <p className="mt-2 text-sm font-semibold">No administrative boundary found</p>}
            <p className="mt-3 text-[10px] font-bold uppercase text-header-foreground/45">Clicked coordinates</p>
            <p className="font-mono text-sm font-semibold text-secondary">{point.latitude.toFixed(6)}° N · {point.longitude.toFixed(6)}° E</p>
             <p className="mt-2 text-xs leading-5 text-header-foreground/55">Rainfall intelligence is shown only when supported for the identified administrative location.</p>
           </> : <p className="mt-2 text-sm leading-6 text-header-foreground/60"><strong className="block text-secondary">Select a location</strong>Click the map to identify the administrative area and view available rainfall intelligence.</p>}
        </div>
         <div className="p-5"><p className="metric-label text-header-foreground/45">Model availability</p><p className="mt-2 text-sm font-semibold text-secondary">{data.coverage === "available" ? "Dhanbad coverage" : "Outside current model coverage"}</p><p className="mt-2 text-xs leading-5 text-header-foreground/55">{data.message}</p></div>
      </aside>
    </div>
    <div className="mx-auto grid max-w-[1600px] gap-8 px-4 py-8 lg:px-6">
       <WeatherSummary data={data} />
       <PredictionPanel data={data} />
       <RainfallChart data={data.history} />
       <AlertsList />
       <ModelInformation />
      <aside className="source-strip" aria-label="Data transparency"><div className="flex items-start gap-3"><Database className="mt-0.5 size-4 text-primary"/><div><p className="metric-label">Scientific data context</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Administrative geometry uses geoBoundaries / DataMeet and LGD 2024. Panchayat records use the project Dhanbad metadata dataset keyed by GPCODE.</p></div></div><p className="text-xs font-semibold text-foreground">Demonstration data · Not an official forecast</p></aside>
    </div>
  </main>;
}

function FlowStep({ label }: { label: string }) { return <p className="text-center text-[9px] font-bold uppercase leading-4 text-header-foreground/75">{label}</p>; }
function Brief({ label, value }: { label: string; value: string }) { return <div className="bg-deep-panel p-3"><p className="text-[9px] font-bold uppercase text-header-foreground/45">{label}</p><p className="mt-1 break-words text-xs font-semibold">{value}</p></div>; }
