---
title: Dark Factory — Earthquake API
status: final
created: 2026-08-13
updated: 2026-08-13
---

## Problem

Consuming USGS earthquake data directly requires engineers to navigate complex GeoJSON structures, verbose URLs, and undocumented filter parameters. There is no clean, single-purpose REST API that exposes real-time global earthquake data in a simple, predictable format ready to feed a map, a dashboard, or an alert agent.

## Goal

Build and deploy a simple, public REST API that proxies the USGS Earthquake Hazards API and exposes real-time worldwide earthquake data — magnitude, depth, and coordinates — through clean endpoints with useful filters. The API supports both JSON and GeoJSON responses. The build is the live demonstration of the Dark Factory development workflow from spec to deployed endpoint.

## Target Users

**Primary:** Software engineers and developers who want to consume earthquake data without dealing with USGS API complexity. The immediate audience is engineers attending the live demo.

**Secondary:** Agents, dashboards, and dynamic maps that need a reliable, filterable earthquake feed.

## What We're Building

A public REST API with the following endpoints:

| Endpoint | Description |
|---|---|
| `GET /earthquakes` | List earthquakes with filters |
| `GET /earthquakes/{id}` | Get a single earthquake by USGS event ID |
| `GET /earthquakes/recent` | Shortcut for last 24 hours, magnitude ≥ 2.5 |
| `GET /health` | Health check — confirms USGS upstream is reachable |

**Supported query filters on `GET /earthquakes`:**

| Parameter | Type | Description |
|---|---|---|
| `minMagnitude` | float | Minimum Richter magnitude |
| `maxMagnitude` | float | Maximum Richter magnitude |
| `startTime` | ISO 8601 | Events after this timestamp |
| `endTime` | ISO 8601 | Events before this timestamp |
| `minDepth` | float (km) | Minimum depth below surface |
| `maxDepth` | float (km) | Maximum depth below surface |
| `latitude` | float | Center latitude for radius filter |
| `longitude` | float | Center longitude for radius filter |
| `radius` | float (km) | Search radius from lat/lon center |
| `limit` | int | Max results returned (default 100, max 500) |

**Response format:** `Accept: application/json` (default) or `Accept: application/geo+json` for native GeoJSON.

## Constraints

- **No auth.** Public API, no API keys required.
- **No persistence.** All data comes directly from USGS in real time — no database, no caching layer for v1.
- **Free-tier deployment.** Must run on a zero-cost cloud platform (Railway, Render, or Fly.io). [ASSUMPTION: final platform decided in architecture step]
- **Upstream dependency.** API availability is tied to USGS uptime. Failures from upstream are surfaced clearly to the consumer.

## Non-Goals

- No frontend, map UI, or dashboard — API only.
- No WebSocket or server-sent events — polling is sufficient for the demo scope.
- No user management, rate limiting, or API key issuance in v1.
- No persistent storage or historical data beyond what USGS provides.
- No reverse geocoding (country/city names) in v1. [ASSUMPTION: could be added as a future filter]

## Success Signal

An engineer hits `GET /earthquakes?minMagnitude=5&limit=10` and gets clean, filtered earthquake data in under 300ms. The demo shows the full Dark Factory workflow — spec written, GitHub issue created, branch opened, code implemented, PR merged, and API live on a public URL — in a single live session.

## Open Questions

- Which free-tier cloud platform? (Railway vs Render vs Fly.io — resolved in architecture step)
- What framework/language for the API? (resolved in architecture step)
