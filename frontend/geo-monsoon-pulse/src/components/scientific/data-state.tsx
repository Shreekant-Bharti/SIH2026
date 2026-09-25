import { CircleAlert, Database, LoaderCircle } from "lucide-react";
import type { DataState } from "@/types/monsoon";

export function DataStatePanel({ state, title, message }: { state: DataState; title: string; message: string }) {
  const Icon = state === "loading" ? LoaderCircle : state === "error" ? CircleAlert : Database;
  return <div className="scientific-panel grid min-h-48 place-items-center px-5 py-8 text-center" role={state === "error" ? "alert" : "status"}>
    <div className="max-w-md"><Icon className={`mx-auto size-5 text-primary ${state === "loading" ? "animate-spin" : ""}`} /><p className="metric-label mt-3">{title}</p><p className="mt-2 text-sm leading-6 text-muted-foreground">{message}</p></div>
  </div>;
}