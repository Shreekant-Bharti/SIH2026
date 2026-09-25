import { CloudRainWind } from "lucide-react";

const projectFacts = [
  { label: "Project", value: "SIH 2026", mono: true },
  { label: "Team", value: "DataNomads" },
  { label: "Model coverage", value: "Dhanbad, Jharkhand" },
] as const;

const provenance = [
  { label: "Administrative boundaries", value: "LGD / verified geographic datasets" },
  { label: "Panchayat metadata", value: "Project Dhanbad Panchayat Dataset" },
  { label: "Model", value: "Ridge Residual", mono: true },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-jet-stream bg-blue-whale text-header-foreground" aria-labelledby="footer-brand">
      <div className="mx-auto max-w-[1600px] px-4 py-4 lg:px-6">
        <div className="grid gap-4 md:grid-cols-[minmax(0,1.35fr)_minmax(420px,1fr)] md:items-start md:gap-12">
          <div className="max-w-xl">
            <div className="flex items-center gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-header-foreground/25 bg-header-foreground/5" aria-hidden="true">
                <CloudRainWind className="size-5" />
              </span>
              <div>
                <h2 id="footer-brand" className="text-sm font-extrabold uppercase">MonsoonScope</h2>
                <p className="mt-0.5 text-[10px] font-semibold uppercase text-jet-stream">Panchayat-Level Rainfall Intelligence</p>
              </div>
            </div>
            <p className="mt-3 max-w-lg text-sm leading-5 text-header-foreground/65">
              Localized rainfall intelligence through geospatial data and ML-based downscaling.
            </p>
          </div>

          <dl className="grid gap-2 sm:grid-cols-3 sm:gap-x-6">
            {projectFacts.map(({ label, value, ...fact }) => (
              <div key={label} className="flex items-baseline justify-between gap-4 sm:block">
                <dt className="text-[10px] font-bold uppercase text-jet-stream/75">{label}</dt>
                <dd className={`text-right text-sm font-semibold text-header-foreground sm:mt-1 sm:text-left ${"mono" in fact ? "font-mono" : ""}`}>{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <section className="mt-4 border-t border-header-foreground/15 pt-3" aria-labelledby="footer-provenance">
          <h3 id="footer-provenance" className="text-[10px] font-bold uppercase text-jet-stream/75">Data &amp; provenance</h3>
          <dl className="mt-2 grid gap-x-8 gap-y-2 md:grid-cols-3">
            {provenance.map(({ label, value, ...source }) => (
              <div key={label} className="flex min-w-0 items-baseline justify-between gap-4 md:block">
                <dt className="text-xs font-semibold text-header-foreground/55">{label}</dt>
                <dd className={`max-w-[58%] text-right text-xs text-header-foreground/85 md:mt-0.5 md:max-w-none md:text-left ${"mono" in source ? "font-mono" : ""}`}>{value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <div className="mt-3 flex flex-col gap-1 border-t border-header-foreground/15 pt-3 text-[11px] text-header-foreground/50 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 MonsoonScope · DataNomads</p>
          <p><span className="font-mono">SIH 2026</span> · Demonstration Platform</p>
        </div>
      </div>
    </footer>
  );
}