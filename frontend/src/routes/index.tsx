import { createFileRoute } from "@tanstack/react-router";
import { Dashboard } from "@/components/dashboard/dashboard";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "MonsoonScope — Panchayat-Level Rainfall Intelligence" },
    { name: "description", content: "Scientific GIS for Panchayat-level rainfall downscaling and localized rainfall analysis in Dhanbad, Jharkhand." },
    { property: "og:title", content: "MonsoonScope — Panchayat-Level Rainfall Intelligence" },
    { property: "og:description", content: "Explore administrative geography and the Ridge Residual rainfall-downscaling workflow." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: Dashboard,
});
