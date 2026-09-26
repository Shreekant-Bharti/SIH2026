import { Link, useRouterState } from "@tanstack/react-router";
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  CloudRainWind,
  FlaskConical,
  History,
  Map,
  Menu,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { SiteFooter } from "@/components/layout/site-footer";
import { backendClient } from "@/services/backend-client";

const links = [
  { to: "/", label: "Dashboard", icon: BarChart3 },
  { to: "/map", label: "Interactive Map", icon: Map },
  { to: "/rainfall", label: "Rainfall", icon: BarChart3 },
  { to: "/predictions", label: "Rainfall Prediction", icon: CloudRainWind },
  { to: "/history", label: "History", icon: History },
  { to: "/alerts", label: "Advisory", icon: AlertTriangle },
  { to: "/methodology", label: "Methodology", icon: BookOpen },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [modelStatus, setModelStatus] = useState<"checking" | "online" | "unavailable">("checking");
  const path = useRouterState({ select: (state) => state.location.pathname });
  useEffect(() => {
    let active = true;
    void backendClient
      .getHealth()
      .then((health) => {
        if (active) setModelStatus(health.model_loaded ? "online" : "unavailable");
      })
      .catch(() => {
        if (active) setModelStatus("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);
  const statusLabel =
    modelStatus === "online"
      ? "Model service online"
      : modelStatus === "checking"
        ? "Checking model service"
        : "Model service unavailable";
  const statusColor = modelStatus === "online" ? "bg-success" : "bg-watch";
  return (
    <div className="min-h-screen bg-background font-sans text-foreground antialiased">
      <header className="sticky top-0 z-40 border-b border-header-foreground/15 bg-header text-header-foreground">
        <div className="flex h-16 items-center justify-between gap-4 px-4 lg:px-6">
          <Link
            to="/"
            className="flex min-w-0 items-center gap-3"
            aria-label="MonsoonScope dashboard"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-header-foreground/25 bg-header-foreground/10">
              <CloudRainWind className="size-5" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-extrabold uppercase">MonsoonScope</span>
              <span className="block truncate text-[9px] font-medium uppercase text-header-foreground/65">
                Panchayat-level rainfall intelligence
              </span>
            </span>
          </Link>
          <nav className="hidden h-full items-center xl:flex" aria-label="Primary navigation">
            {links.map(({ to, label }) => (
              <Link
                to={to}
                key={to}
                className={cn(
                  "flex h-full items-center border-b-2 border-transparent px-3 text-xs font-semibold text-header-foreground/65 transition-colors hover:bg-header-foreground/5 hover:text-header-foreground",
                  path === to && "border-header-foreground bg-header-foreground text-header",
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-4 md:flex">
              <span className="flex items-center gap-2 text-[10px] font-bold uppercase text-header-foreground/85">
                <span className={cn("size-1.5 rounded-full", statusColor)} />
                {statusLabel}
              </span>
              <span className="flex items-center gap-2 border-l border-header-foreground/20 pl-4 text-[10px] font-semibold uppercase text-header-foreground/60">
                <FlaskConical className="size-3.5" />
                SIH 2026
              </span>
            </div>
            <button
              className="rounded-md p-2 text-header-foreground transition-colors hover:bg-header-foreground/10 xl:hidden"
              aria-label="Toggle navigation"
              onClick={() => setOpen((value) => !value)}
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </div>
        {open && (
          <nav className="grid border-t border-header-foreground/15 bg-header p-2 xl:hidden">
            {links.map(({ to, label, icon: Icon }) => (
              <Link
                to={to}
                onClick={() => setOpen(false)}
                key={to}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-3 text-sm text-header-foreground/70",
                  path === to && "bg-header-foreground text-header",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            ))}
          </nav>
        )}
      </header>
      {children}
      <SiteFooter />
    </div>
  );
}
