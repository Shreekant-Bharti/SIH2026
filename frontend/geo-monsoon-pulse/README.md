# Monsoon Navigator

Build a production-quality frontend for an SIH 2026 project called:

Hyperlocal Monsoon Onset & Break Prediction System

The application is designed to provide hyperlocal monsoon information and ML-based predictions at a very granular geographic level:

India → State → District → Block → Panchayat

The most important feature of this application is a geographic drill-down experience where users progressively select a location and the map transitions from the national level to the selected state, then district, then block, and finally panchayat.

This should NOT look like a generic AI-generated dashboard.

The visual identity should feel like a serious meteorological / GIS / scientific data product used by researchers, administrators, disaster-management teams, agriculture departments, and technically informed users.

Use real weather-product interfaces as inspiration for information hierarchy and map interaction, but do NOT copy their designs.

References for inspiration:

Ventusky — map-first weather visualization

meteoblue — scientific weather data and charts

RainViewer — precipitation/rainfall visualization

Do not copy logos, layouts, branding, colors, or proprietary UI elements from these products.

==================================================
TECHNOLOGY

Use:

React

TypeScript

Vite

Tailwind CSS

A professional mapping library such as MapLibre GL JS or Leaflet

Recharts or another reliable charting library

Lucide icons

Component-based architecture

Keep the architecture clean and modular because the frontend will later connect to a FastAPI/ML backend.

Do not create unnecessary dependencies.

==================================================
CORE PRODUCT PHILOSOPHY

The map is the primary interaction mechanism.

The user should feel like they are navigating geographically:

India
↓
Jharkhand
↓
Dhanbad
↓
Sindri
↓
Panchayat

The selected geographic level should determine what information is displayed.

The application should not overwhelm the user with dozens of cards.

Prioritize:

Geography

Rainfall

Monsoon onset prediction

Monsoon break prediction

Historical trends

Alerts

Explainable prediction

==================================================
VISUAL STYLE

IMPORTANT:

Avoid the stereotypical "AI website" appearance.

DO NOT use:

Excessive gradients

Purple AI gradients

Neon glowing borders

Glassmorphism everywhere

Excessive rounded cards

Floating futuristic UI

Robot illustrations

AI-generated abstract backgrounds

Giant "AI POWERED" labels

Excessive animations

Excessive shadows

Random decorative elements

Instead create a:

clean + scientific + geographic + meteorological + modern interface

Visual characteristics:

Light neutral background

Strong map focus

Dark readable typography

Restrained use of color

Clear geographic hierarchy

Thin borders

Moderate corner radius

Subtle shadows only where necessary

Strong information hierarchy

Professional charts

Clear legends

Dense but readable data presentation

The interface should feel closer to a professional GIS/weather monitoring platform than a SaaS landing page.

==================================================
COLOR SYSTEM

Use a restrained meteorological palette.

Primary:
Deep navy / dark blue

Secondary:
Muted blue

Rain:
Blue shades

Temperature:
Warm amber/orange

Normal:
Green

Warning:
Amber

Severe:
Red

Background:
Off-white / very light neutral

Do not use gradients as a primary design element.

Ensure WCAG-readable contrast.

==================================================
APPLICATION STRUCTURE

Create these main sections:

Dashboard

Interactive Map

Predictions

Rainfall Analytics

Alerts

Historical Data

About / Methodology

Use a clean top navigation or sidebar depending on what provides the best map experience.

The map should remain visually dominant.

==================================================
LOCATION HIERARCHY

Create a reusable location hierarchy component:

State
→ District
→ Block
→ Panchayat

The selected location should be displayed as a breadcrumb:

India / Jharkhand / Dhanbad / Sindri / Panchayat Name

Each level should be independently selectable.

Initially use realistic mock geographic data and clear placeholder GeoJSON interfaces.

Do NOT hardcode the architecture in a way that prevents later replacement with real GeoJSON.

Create clean interfaces/types for:

State

District

Block

Panchayat

GeoJSON feature

Weather observation

Rainfall forecast

Monsoon prediction

Alert

==================================================
MAP EXPERIENCE

The map should support:

Zoom

Pan

Geographic boundaries

Hover state

Selected region state

Highlighted boundary

Map legend

Reset view

Zoom controls

Current selection

Layer controls

The map must support hierarchical drill-down.

When a user selects a state:

Highlight that state.

Zoom smoothly to its geographic bounds.

Display district boundaries inside it.

Update breadcrumb.

Update the information panel.

When a district is selected:

Zoom to district bounds.

Display block boundaries.

Update breadcrumb.

Update relevant data.

When a block is selected:

Zoom to block bounds.

Display panchayat boundaries.

Update breadcrumb.

When a panchayat is selected:

Zoom to the panchayat.

Highlight its boundary.

Show the panchayat-level weather and prediction information.

Do not literally crop an image.

Use geographic geometry and map bounds / fitBounds behavior.

==================================================
MOCK DATA

Until backend integration is implemented, create a realistic mock-data layer.

Do not scatter mock data throughout components.

Keep mock data in dedicated files/services so that it can later be replaced with API calls.

Example hierarchy:

India
→ Jharkhand
→ Dhanbad
→ Sindri
→ Panchayat examples

Create enough mock data to demonstrate the complete drill-down interaction.

==================================================
DASHBOARD

The dashboard should immediately communicate:

Selected location

Current rainfall

Temperature

Humidity

Rainfall forecast

Monsoon status

Onset probability

Break probability

Active alerts

The top section should show:

Location breadcrumb

State / District / Block / Panchayat selectors

Then:

Large interactive map

Then:

Compact weather summary

Then:

Monsoon prediction summary

Then:

Rainfall trend

Then:

Alerts

Do not create 15+ cards.

==================================================
PREDICTION DESIGN

The system predicts:

Monsoon Onset

Monsoon Break

Display predictions clearly.

Example:

MONSOON ONSET

Expected:
24 June

Probability:
87%

Confidence:
High

MONSOON BREAK

Expected:
18–21 July

Probability:
34%

Confidence:
Moderate

Do not present these as guaranteed forecasts.

Use wording such as:

"Model prediction"

"Probability"

"Confidence"

==================================================
EXPLAINABLE AI

Create an explainability section.

Example:

WHY IS A MONSOON BREAK BEING PREDICTED?

Rainfall has decreased over the previous 3 days

Relative humidity trend is declining

Temperature anomaly is increasing

Atmospheric pressure trend is changing

Historical patterns show similarity

Show these as evidence factors rather than decorative AI cards.

Create the UI so that actual backend/model explanations can later replace the mock values.

==================================================
RAINFALL ANALYTICS

Create professional charts for:

Daily rainfall

Cumulative rainfall

Predicted vs observed rainfall

Rainfall anomaly

7-day trend

30-day trend

Use clean charts.

Avoid unnecessary chart decorations.

Include:

7D
30D
90D
Monsoon Season

filters.

==================================================
ALERTS

Create an alert system with:

Normal
Watch
Warning
Severe

Each alert should contain:

Location
Time
Expected rainfall
Severity
Reason
Recommended action

Use restrained colors and clear severity indicators.

==================================================
RESPONSIVENESS

The application must work properly on:

Desktop
Laptop
Tablet
Mobile

Desktop should prioritize the map.

On mobile:

Map remains usable

Location selectors become stacked

Information panels become vertically scrollable

Charts remain readable

Navigation becomes compact

Do not simply shrink the desktop interface.

==================================================
CODE QUALITY

Use reusable components.

Suggested structure:

components/
map/
location/
weather/
predictions/
analytics/
alerts/
layout/

data/
services/
types/
hooks/

Keep business logic separate from presentation.

Use TypeScript types throughout.

Do not put huge amounts of logic inside App.tsx.

Create reusable components for:

LocationSelector
LocationBreadcrumb
WeatherSummary
PredictionCard
PredictionExplanation
RainfallChart
AlertCard
MapLegend
MapControls
MapContainer

==================================================
IMPORTANT

Do NOT build the entire application as a generic AI dashboard.

The defining visual identity should be:

Geographic navigation + meteorological data + scientific visualization.

The map and geographic drill-down should be the central experience.

Start with the frontend architecture and main Dashboard screen.

Use realistic mock data.

Make the implementation modular so that real GeoJSON and FastAPI endpoints can be integrated later.

Do not implement authentication, payments, unnecessary user profiles, or unrelated SaaS functionality.  take reference from compaititior websites 1. Ventusky, 2. meteoblue, 3. RainViewer

## Development

You need Node.js ≥ 18 and either `npm` or `bun`.

```sh
# Clone the repo and navigate to the frontend
cd frontend/geo-monsoon-pulse

# Install dependencies
bun install   # or: npm install

# Start the dev server
bun run dev   # or: npm run dev
```

The app will be available at `http://localhost:3000` by default.

## Project Structure

```
src/
├── components/       # Reusable UI components (map, weather, alerts, etc.)
├── routes/           # TanStack Router page routes
├── data/             # Mock data (to be replaced with API calls)
├── services/         # API service layer
├── hooks/            # Custom React hooks
├── types/            # TypeScript type definitions
├── config/           # App-level configuration
└── lib/              # Utility libraries
```
