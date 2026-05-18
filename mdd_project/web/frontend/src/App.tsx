import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, {
  type Map,
  type GeoJSONSource,
  type MapMouseEvent,
  type MapGeoJSONFeature,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./App.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface SpeciesRecord {
  species_id: number;
  sci_name: string;
  sci_name_space: string;
  main_common_name: string | null;
  order: string;
  family: string;
  iucn_status: string | null;
  extinct: boolean;
  type_lat: number | null;
  type_lon: number | null;
  type_locality: string | null;
  country_distribution: string | null;
}

interface OccurrenceMeta {
  count: number;
  limit: number;
}

interface TypeLocFC {
  type: string;
  features: object[];
  meta: { count: number; limit: number };
}

// IUCN status → colour
const IUCN_COLOR: Record<string, string> = {
  LC: "#4caf7d",
  NT: "#a8d86e",
  VU: "#f0c74a",
  EN: "#f0a44a",
  CR: "#e05f5f",
  EW: "#b07ad4",
  EX: "#888",
  DD: "#aaa",
};
function iucnColor(status: string | null): string {
  return IUCN_COLOR[status ?? ""] ?? "#4f9cf9";
}

// ---------------------------------------------------------------------------
// API helpers (proxied via /api → FastAPI :8000)
// ---------------------------------------------------------------------------
const API = "/api";

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Build a single-species type-locality GeoJSON (0 or 1 feature)
// ---------------------------------------------------------------------------
function buildSpeciesTypeLoc(sp: SpeciesRecord): TypeLocFC {
  const hasCoords = sp.type_lat != null && sp.type_lon != null;
  return {
    type: "FeatureCollection",
    features: hasCoords
      ? [
          {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [sp.type_lon as number, sp.type_lat as number],
            },
            properties: {
              sci_name: sp.sci_name,
              sci_name_space: sp.sci_name_space,
              main_common_name: sp.main_common_name,
              order: sp.order,
              family: sp.family,
              iucn_status: sp.iucn_status,
              type_locality: sp.type_locality,
            },
          },
        ]
      : [],
    meta: { count: hasCoords ? 1 : 0, limit: 1 },
  };
}

// ---------------------------------------------------------------------------
// Map source / layer IDs
// ---------------------------------------------------------------------------
const SRC_TYPE_LOC = "type-localities";
const SRC_OCCURRENCES = "occurrences";
const LYR_TYPE_LOC = "type-localities-circle";
const LYR_OCCURRENCES = "occurrences-circle";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function App() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Cache the full global type-localities dataset so we can toggle back
  // without re-fetching from the server.
  const allTypeLocCacheRef = useRef<TypeLocFC | null>(null);
  // Mirror of `selected` in a ref so effects can read it without stale closures.
  const selectedRef = useRef<SpeciesRecord | null>(null);

  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SpeciesRecord[]>([]);
  const [selected, setSelected] = useState<SpeciesRecord | null>(null);
  const [occurrenceMeta, setOccurrenceMeta] = useState<OccurrenceMeta | null>(null);
  const [loadingOcc, setLoadingOcc] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTypeLocalities, setShowTypeLocalities] = useState(true);
  const [showOccurrences, setShowOccurrences] = useState(true);
  const [typeLocalityCount, setTypeLocalityCount] = useState<number>(0);
  // When a species is selected this is false (show 1 point); user can toggle
  // to true to temporarily display all ~1,941 MDD type localities.
  const [showAllTypeLocalities, setShowAllTypeLocalities] = useState(false);

  // ── Initialise map ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
        sources: {
          "osm-tiles": {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
            maxzoom: 19,
          },
        },
        layers: [
          {
            id: "osm-background",
            type: "raster",
            source: "osm-tiles",
            paint: { "raster-opacity": 0.85, "raster-saturation": -0.4 },
          },
        ],
      },
      center: [0, 20],
      zoom: 1.8,
      minZoom: 0,
      maxZoom: 18,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

    const popup = new maplibregl.Popup({
      closeButton: true,
      closeOnClick: false,
      maxWidth: "300px",
    });
    popupRef.current = popup;

    map.on("load", () => {
      // ── Type localities source + layer ────────────────────────────────────
      map.addSource(SRC_TYPE_LOC, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: LYR_TYPE_LOC,
        type: "circle",
        source: SRC_TYPE_LOC,
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 3,
            8, 7,
          ],
          "circle-color": [
            "match", ["get", "iucn_status"],
            "LC", IUCN_COLOR.LC,
            "NT", IUCN_COLOR.NT,
            "VU", IUCN_COLOR.VU,
            "EN", IUCN_COLOR.EN,
            "CR", IUCN_COLOR.CR,
            "EW", IUCN_COLOR.EW,
            "EX", IUCN_COLOR.EX,
            "DD", IUCN_COLOR.DD,
            "#4f9cf9",
          ],
          "circle-stroke-width": 0.8,
          "circle-stroke-color": "rgba(255,255,255,0.4)",
          "circle-opacity": 0.8,
        },
      });

      // ── Occurrences source + layer ────────────────────────────────────────
      map.addSource(SRC_OCCURRENCES, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: LYR_OCCURRENCES,
        type: "circle",
        source: SRC_OCCURRENCES,
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 4,
            8, 8,
          ],
          "circle-color": "#f0a44a",
          "circle-stroke-width": 1,
          "circle-stroke-color": "rgba(0,0,0,0.5)",
          "circle-opacity": 0.75,
        },
      });

      // ── Load all type localities and cache them ────────────────────────────
      fetchJson<TypeLocFC>(`${API}/type-localities?limit=2000`)
        .then((fc) => {
          allTypeLocCacheRef.current = fc;
          (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
            fc as Parameters<GeoJSONSource["setData"]>[0]
          );
          setTypeLocalityCount(fc.meta.count);
        })
        .catch(console.error);

      // ── Pointer cursor on hover ───────────────────────────────────────────
      for (const lyr of [LYR_TYPE_LOC, LYR_OCCURRENCES]) {
        map.on("mouseenter", lyr, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", lyr, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      // ── Click popups ──────────────────────────────────────────────────────
      map.on("click", LYR_TYPE_LOC, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as Record<string, string | null>;
        const html = `
          <div class="popup-content">
            <h4>${p.sci_name_space ?? p.sci_name ?? ""}</h4>
            ${p.main_common_name ? `<p class="common">${p.main_common_name}</p>` : ""}
            <p><span class="label">Family:</span> ${p.family ?? "—"} · ${p.order ?? "—"}</p>
            ${p.iucn_status ? `<p><span class="label">IUCN:</span> <span class="badge" style="background:${iucnColor(p.iucn_status)}">${p.iucn_status}</span></p>` : ""}
            ${p.type_locality ? `<p class="locality"><span class="label">Type locality:</span> ${p.type_locality}</p>` : ""}
          </div>`;
        popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
      });

      map.on("click", LYR_OCCURRENCES, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as Record<string, string | null>;
        const html = `
          <div class="popup-content">
            <h4>${p.mdd_sci_name ?? p.reported_name ?? "Unknown"}</h4>
            <p><span class="label">Date:</span> ${p.event_date ?? "—"}</p>
            <p><span class="label">Country:</span> ${p.country_code ?? "—"}</p>
            <p><span class="label">Dataset:</span> ${p.dataset_name ?? "—"}</p>
            <p><span class="label">Basis:</span> ${p.basis_of_record ?? "—"}</p>
            ${p.coordinate_uncertainty_m ? `<p><span class="label">Coord. uncertainty:</span> ${p.coordinate_uncertainty_m} m</p>` : ""}
          </div>`;
        popup.setLngLat(e.lngLat).setHTML(html).addTo(map);
      });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Layer visibility toggles ──────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    map.setLayoutProperty(LYR_TYPE_LOC, "visibility", showTypeLocalities ? "visible" : "none");
  }, [showTypeLocalities]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    map.setLayoutProperty(LYR_OCCURRENCES, "visibility", showOccurrences ? "visible" : "none");
  }, [showOccurrences]);

  // ── Toggle: show all MDD type localities vs. selected-species only ─────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (showAllTypeLocalities) {
      // Load all type localities (from cache where possible)
      const cached = allTypeLocCacheRef.current;
      if (cached) {
        (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
          cached as Parameters<GeoJSONSource["setData"]>[0]
        );
        setTypeLocalityCount(cached.meta.count);
      } else {
        fetchJson<TypeLocFC>(`${API}/type-localities?limit=2000`)
          .then((fc) => {
            allTypeLocCacheRef.current = fc;
            (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
              fc as Parameters<GeoJSONSource["setData"]>[0]
            );
            setTypeLocalityCount(fc.meta.count);
          })
          .catch(console.error);
      }
    } else {
      // Revert to species-only view — use ref to avoid stale closure over `selected`
      const sp = selectedRef.current;
      if (sp) {
        const fc = buildSpeciesTypeLoc(sp);
        (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
          fc as Parameters<GeoJSONSource["setData"]>[0]
        );
        setTypeLocalityCount(fc.meta.count);
      }
    }
  }, [showAllTypeLocalities]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Species search ────────────────────────────────────────────────────────
  const handleQueryChange = useCallback(async (value: string) => {
    setQuery(value);
    setError(null);
    if (value.length < 3) {
      setSuggestions([]);
      return;
    }
    try {
      const results = await fetchJson<SpeciesRecord[]>(`${API}/species?limit=10`);
      const q = value.toLowerCase();
      setSuggestions(
        results.filter(
          (r) =>
            r.sci_name.toLowerCase().includes(q) ||
            (r.main_common_name ?? "").toLowerCase().includes(q)
        )
      );
    } catch {
      setError("Search failed — is the API running?");
    }
  }, []);

  const handleSearchSubmit = useCallback(async (name: string) => {
    if (!name.trim()) return;
    setError(null);
    try {
      const sp = await fetchJson<SpeciesRecord>(
        `${API}/species/${encodeURIComponent(name.trim())}`
      );
      selectSpecies(sp);
    } catch {
      setError(`Species "${name}" not found in MDD v2.4`);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectSpecies = useCallback(async (sp: SpeciesRecord) => {
    setSelected(sp);
    selectedRef.current = sp;
    setSuggestions([]);
    setQuery(sp.sci_name_space ?? sp.sci_name);
    setError(null);
    setOccurrenceMeta(null);
    setShowAllTypeLocalities(false); // always start in single-species mode

    const map = mapRef.current;
    if (!map) return;

    // Filter type locality layer to this species only (0 or 1 point)
    const speciesFC = buildSpeciesTypeLoc(sp);
    (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
      speciesFC as Parameters<GeoJSONSource["setData"]>[0]
    );
    setTypeLocalityCount(speciesFC.meta.count);

    // Fly to type locality if coordinates exist
    if (sp.type_lat != null && sp.type_lon != null) {
      map.flyTo({ center: [sp.type_lon, sp.type_lat], zoom: 5, duration: 1200 });
    }

    // Load GBIF occurrences
    setLoadingOcc(true);
    try {
      const fc = await fetchJson<{
        features: object[];
        meta: OccurrenceMeta;
        type: string;
      }>(`${API}/occurrences/${encodeURIComponent(sp.sci_name)}`);

      (map.getSource(SRC_OCCURRENCES) as GeoJSONSource).setData(
        fc as Parameters<GeoJSONSource["setData"]>[0]
      );
      setOccurrenceMeta(fc.meta);

      if (fc.features.length > 0) {
        const coords = fc.features
          .map((f) => (f as { geometry: { coordinates: [number, number] } }).geometry.coordinates)
          .filter((c) => c && c.length === 2);
        if (coords.length) {
          const lngs = coords.map((c) => c[0]);
          const lats = coords.map((c) => c[1]);
          map.fitBounds(
            [
              [Math.min(...lngs), Math.min(...lats)],
              [Math.max(...lngs), Math.max(...lats)],
            ],
            { padding: 60, maxZoom: 8, duration: 1000 }
          );
        }
      }
    } catch {
      (map.getSource(SRC_OCCURRENCES) as GeoJSONSource).setData({
        type: "FeatureCollection",
        features: [],
      });
      setOccurrenceMeta({ count: 0, limit: 500 });
    } finally {
      setLoadingOcc(false);
    }
  }, []);

  // ── Clear selected species and restore global view ────────────────────────
  const clearSpecies = useCallback(() => {
    setSelected(null);
    selectedRef.current = null;
    setQuery("");
    setSuggestions([]);
    setOccurrenceMeta(null);
    setShowAllTypeLocalities(false);
    setError(null);

    const map = mapRef.current;
    if (!map) return;

    // Clear occurrences
    (map.getSource(SRC_OCCURRENCES) as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: [],
    });

    // Restore all type localities from cache
    const cached = allTypeLocCacheRef.current;
    if (cached) {
      (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
        cached as Parameters<GeoJSONSource["setData"]>[0]
      );
      setTypeLocalityCount(cached.meta.count);
    }
  }, []);

  // ── Derived display values ────────────────────────────────────────────────
  const typeLocLayerLabel =
    selected && !showAllTypeLocalities
      ? "Type locality (selected species)"
      : "All MDD type localities";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="layout">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <header className="sidebar-header">
          <span className="logo">🦔 MDD</span>
          <span className="logo-sub">Mammal Diversity Database v2.4</span>
        </header>

        {/* Search */}
        <section className="section">
          <label className="section-label">Species search</label>
          <div className="search-wrap">
            <div className="search-input-row">
              <input
                className="search-input"
                type="text"
                placeholder="e.g. Ursus arctos, galago…"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearchSubmit(query);
                }}
              />
              {selected && (
                <button className="clear-btn" onClick={clearSpecies} title="Clear selection">
                  ×
                </button>
              )}
            </div>
            {suggestions.length > 0 && (
              <ul className="suggestions">
                {suggestions.map((s) => (
                  <li key={s.species_id} onClick={() => selectSpecies(s)}>
                    <span className="sug-sci">{s.sci_name_space}</span>
                    {s.main_common_name && (
                      <span className="sug-common">{s.main_common_name}</span>
                    )}
                    <span className="sug-family">{s.family}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {error && <p className="error-msg">{error}</p>}
        </section>

        {/* Selected species info */}
        {selected && (
          <section className="section species-card">
            <div className="species-sci">{selected.sci_name_space}</div>
            {selected.main_common_name && (
              <div className="species-common">{selected.main_common_name}</div>
            )}
            <div className="species-meta">
              <span>{selected.order}</span>
              <span className="sep">›</span>
              <span>{selected.family}</span>
            </div>
            {selected.iucn_status && (
              <div
                className="iucn-badge"
                style={{ background: iucnColor(selected.iucn_status) }}
              >
                {selected.iucn_status}
              </div>
            )}
            {selected.country_distribution && (
              <p className="countries">
                <span className="label">Range:</span>{" "}
                {selected.country_distribution}
              </p>
            )}
            {selected.type_locality ? (
              <p className="type-locality-text">
                <span className="label">Type locality:</span>{" "}
                {selected.type_locality}
                {selected.type_lat == null && (
                  <span className="no-coords"> (no geocoded coordinates in MDD v2.4)</span>
                )}
              </p>
            ) : null}
            <div className="occ-status">
              {loadingOcc ? (
                <span className="loading">Loading occurrences…</span>
              ) : occurrenceMeta ? (
                occurrenceMeta.count > 0 ? (
                  <span className="occ-count">
                    🔵 {occurrenceMeta.count} GBIF occurrences loaded
                  </span>
                ) : (
                  <span className="occ-empty">
                    No occurrences in DB yet — run:
                    <code>
                      {"python mdd_project/scripts/gbif_import.py --species \"" +
                        (selected.sci_name_space ?? selected.sci_name.replace(/_/g, " ")) +
                        "\" --limit 200"}
                    </code>
                  </span>
                )
              ) : null}
            </div>
          </section>
        )}

        {/* Layer toggles */}
        <section className="section">
          <label className="section-label">Layers</label>

          {/* Type localities row */}
          <div className="layer-row">
            <label className="toggle">
              <input
                type="checkbox"
                checked={showTypeLocalities}
                onChange={(e) => setShowTypeLocalities(e.target.checked)}
              />
              <span className="dot" style={{ background: "#4f9cf9" }} />
              {typeLocLayerLabel}
            </label>
            <span className="layer-count">{typeLocalityCount.toLocaleString()}</span>
          </div>

          {/* "Show all" sub-toggle — only appears when a species is selected */}
          {selected && (
            <div className="layer-row layer-sub">
              <label className="toggle toggle-sub">
                <input
                  type="checkbox"
                  checked={showAllTypeLocalities}
                  onChange={(e) => setShowAllTypeLocalities(e.target.checked)}
                />
                <span className="dot dot-dim" style={{ background: "#4f9cf9" }} />
                Show all MDD type localities
              </label>
            </div>
          )}

          {/* Help text when in species mode */}
          {selected && !showAllTypeLocalities && (
            <p className="type-loc-help">
              Type locality = holotype collection site. One per accepted species in MDD.
            </p>
          )}
          {/* Hint in global (no species selected) mode */}
          {!selected && (
            <p className="layer-hint">~1,941 species have geocoded coords in MDD v2.4 · coloured by IUCN status</p>
          )}

          {/* GBIF occurrences row */}
          <div className="layer-row" style={{ marginTop: selected ? 8 : 0 }}>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showOccurrences}
                onChange={(e) => setShowOccurrences(e.target.checked)}
              />
              <span className="dot" style={{ background: "#f0a44a" }} />
              GBIF occurrences
            </label>
            {occurrenceMeta && (
              <span className="layer-count">{occurrenceMeta.count.toLocaleString()}</span>
            )}
          </div>
          <p className="layer-hint">Where the species has been reported (GBIF occurrences)</p>
        </section>

        {/* About these layers — collapsible explainer */}
        <section className="section">
          <details className="about-layers">
            <summary className="about-summary">About these layers</summary>
            <div className="about-body">
              <p>
                <strong>MDD</strong> is a mammal taxonomy authority, not a museum
                catalogue. Each accepted species has at most one type locality — the
                site where its holotype specimen was collected. Of ~14,000 valid
                species, roughly 1,941 have geocoded coordinates in MDD v2.4; the
                rest have text descriptions only, so no map point appears.
              </p>
              <p>
                <strong>GBIF occurrences</strong> are independent sighting and
                specimen records sourced from GBIF. A species
                can have no type locality dot (coordinates absent from MDD) yet many
                GBIF records, or vice versa — the two layers are separate datasets.
              </p>
            </div>
          </details>
        </section>

        {/* IUCN legend */}
        <section className="section">
          <label className="section-label">IUCN (type localities)</label>
          <div className="legend">
            {Object.entries(IUCN_COLOR).map(([code, color]) => (
              <div key={code} className="legend-row">
                <span className="legend-dot" style={{ background: color }} />
                <span>{code}</span>
              </div>
            ))}
          </div>
        </section>

        <footer className="sidebar-footer">
          Data:{" "}
          <a href="https://www.mammaldiversity.org/" target="_blank" rel="noreferrer">
            MDD v2.4
          </a>{" "}
          · Occurrences:{" "}
          <a href="https://gbif.org" target="_blank" rel="noreferrer">
            GBIF
          </a>
        </footer>
      </aside>

      {/* ── Map ─────────────────────────────────────────────────────────── */}
      <div ref={mapContainer} className="map-container" />
    </div>
  );
}
