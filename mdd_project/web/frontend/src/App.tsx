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
type Rank = "species" | "genus" | "family";

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

interface TaxonResult {
  rank: "genus" | "family";
  name: string;
  species_count: number;
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

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function popupDetailRow(label: string, value: string): string {
  return `<dt>${label}</dt><dd>${value}</dd>`;
}

function typeLocalityPopupHtml(p: Record<string, string | null>): string {
  const museumLocation =
    p.museum_location != null && String(p.museum_location).trim() !== "" && String(p.museum_location).toUpperCase() !== "NA"
      ? escapeHtml(String(p.museum_location).trim())
      : null;
  const museum =
    p.museum_name != null && String(p.museum_name).trim() !== ""
      ? escapeHtml(String(p.museum_name)) +
        (p.museum_abbreviation ? ` <span class="popup-abbr">(${escapeHtml(String(p.museum_abbreviation))})</span>` : "") +
        (museumLocation ? `<span class="popup-museum-location">${museumLocation}</span>` : "")
      : null;
  const voucher =
    p.type_voucher != null && String(p.type_voucher).trim() !== ""
      ? escapeHtml(String(p.type_voucher))
      : null;
  const kind =
    p.type_kind != null && String(p.type_kind).trim() !== ""
      ? escapeHtml(String(p.type_kind))
      : null;
  const uri =
    p.type_voucher_uris != null && String(p.type_voucher_uris).trim().startsWith("http")
      ? escapeHtml(String(p.type_voucher_uris).trim())
      : null;

  const specimenValue = voucher
    ? `${kind ? `<span class="popup-specimen-kind">${kind}</span>` : ""}${kind ? '<span class="popup-specimen-sep">·</span>' : ""}<code class="popup-catalog">${voucher}</code>`
    : null;

  const details: string[] = [];
  if (p.type_locality) {
    details.push(popupDetailRow("Type locality", escapeHtml(String(p.type_locality))));
  }
  if (museum) details.push(popupDetailRow("Museum", museum));
  if (specimenValue) details.push(popupDetailRow("Type specimen", specimenValue));

  return `
    <div class="popup-content popup-content--type-loc">
      <header class="popup-header">
        <h4 class="popup-sci">${escapeHtml(String(p.sci_name_space ?? p.sci_name ?? ""))}</h4>
        ${p.main_common_name ? `<p class="popup-common">${escapeHtml(String(p.main_common_name))}</p>` : ""}
        <div class="popup-chips">
          ${p.family ? `<span class="popup-chip">${escapeHtml(String(p.family))}</span>` : ""}
          ${p.order ? `<span class="popup-chip popup-chip-dim">${escapeHtml(String(p.order))}</span>` : ""}
          ${p.iucn_status ? `<span class="popup-badge" style="background:${iucnColor(p.iucn_status)}">${escapeHtml(String(p.iucn_status))}</span>` : ""}
        </div>
      </header>
      ${details.length ? `<dl class="popup-details">${details.join("")}</dl>` : ""}
      ${uri ? `<footer class="popup-footer"><a class="popup-link" href="${uri}" target="_blank" rel="noopener noreferrer">View in collection ↗</a></footer>` : ""}
    </div>`;
}

// ---------------------------------------------------------------------------
// Map source / layer IDs
// ---------------------------------------------------------------------------
const SRC_TYPE_LOC = "type-localities";
const SRC_OCCURRENCES = "occurrences";
const LYR_TYPE_LOC = "type-localities-circle";
const LYR_OCCURRENCES = "occurrences-circle";

// Neutral light basemap — keeps IUCN / GBIF colours readable vs colourful OSM
const BASEMAP_TILES =
  "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png";
const BASEMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

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

  const [rank, setRank] = useState<Rank>("species");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SpeciesRecord[]>([]);
  const [taxonSuggestions, setTaxonSuggestions] = useState<TaxonResult[]>([]);
  const [selected, setSelected] = useState<SpeciesRecord | null>(null);
  const [selectedTaxon, setSelectedTaxon] = useState<TaxonResult | null>(null);
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
          basemap: {
            type: "raster",
            tiles: [BASEMAP_TILES],
            tileSize: 256,
            attribution: BASEMAP_ATTRIBUTION,
            maxzoom: 19,
          },
        },
        layers: [
          {
            id: "basemap",
            type: "raster",
            source: "basemap",
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
          "circle-stroke-width": 1,
          "circle-stroke-color": "rgba(30,30,40,0.55)",
          "circle-opacity": 0.9,
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
        popup.setLngLat(e.lngLat).setHTML(typeLocalityPopupHtml(p)).addTo(map);
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
        fetchJson<TypeLocFC>(
          `${API}/type-localities?species=${encodeURIComponent(sp.sci_name)}&limit=1`
        )
          .then((fc) => {
            (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
              fc as Parameters<GeoJSONSource["setData"]>[0]
            );
            setTypeLocalityCount(fc.meta.count);
          })
          .catch(console.error);
      }
    }
  }, [showAllTypeLocalities]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Search (species / genus / family) ────────────────────────────────────
  const handleQueryChange = useCallback(async (value: string, currentRank: Rank) => {
    setQuery(value);
    setError(null);
    setSuggestions([]);
    setTaxonSuggestions([]);
    if (value.length < 2) return;
    try {
      if (currentRank === "species") {
        const results = await fetchJson<SpeciesRecord[]>(`${API}/species?limit=10`);
        const q = value.toLowerCase();
        setSuggestions(
          results.filter(
            (r) =>
              r.sci_name.toLowerCase().includes(q) ||
              (r.main_common_name ?? "").toLowerCase().includes(q)
          )
        );
      } else {
        const results = await fetchJson<TaxonResult[]>(
          `${API}/taxonomy/search?q=${encodeURIComponent(value)}&rank=${currentRank}`
        );
        setTaxonSuggestions(results);
      }
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
    setSelectedTaxon(null);
    selectedRef.current = sp;
    setSuggestions([]);
    setTaxonSuggestions([]);
    setQuery(sp.sci_name_space ?? sp.sci_name);
    setError(null);
    setOccurrenceMeta(null);
    setShowAllTypeLocalities(false); // always start in single-species mode

    const map = mapRef.current;
    if (!map) return;

    // Filter type locality layer to this species only (0 or 1 point, incl. museum)
    try {
      const speciesFC = await fetchJson<TypeLocFC>(
        `${API}/type-localities?species=${encodeURIComponent(sp.sci_name)}&limit=1`
      );
      (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
        speciesFC as Parameters<GeoJSONSource["setData"]>[0]
      );
      setTypeLocalityCount(speciesFC.meta.count);
    } catch {
      setTypeLocalityCount(0);
    }

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

  // ── Select a genus or family — load all member type localities ───────────
  const selectTaxon = useCallback(async (t: TaxonResult) => {
    setSelectedTaxon(t);
    setSelected(null);
    selectedRef.current = null;
    setSuggestions([]);
    setTaxonSuggestions([]);
    setQuery(t.name);
    setError(null);
    setOccurrenceMeta(null);
    setShowAllTypeLocalities(false);

    const map = mapRef.current;
    if (!map) return;

    // Clear GBIF occurrences (loaded per-species only)
    (map.getSource(SRC_OCCURRENCES) as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: [],
    });

    // Load type localities for every species in this taxon
    const paramKey = t.rank === "genus" ? "genus" : "family";
    try {
      const fc = await fetchJson<TypeLocFC>(
        `${API}/type-localities?${paramKey}=${encodeURIComponent(t.name)}&limit=2000`
      );
      (map.getSource(SRC_TYPE_LOC) as GeoJSONSource).setData(
        fc as Parameters<GeoJSONSource["setData"]>[0]
      );
      setTypeLocalityCount(fc.meta.count);

      // Fit map bounds to the loaded features
      const coords = (fc.features as Array<{ geometry: { coordinates: [number, number] } }>)
        .map((f) => f.geometry.coordinates)
        .filter((c) => c && c.length === 2);
      if (coords.length) {
        const lngs = coords.map((c) => c[0]);
        const lats = coords.map((c) => c[1]);
        map.fitBounds(
          [
            [Math.min(...lngs), Math.min(...lats)],
            [Math.max(...lngs), Math.max(...lats)],
          ],
          { padding: 80, maxZoom: 6, duration: 1200 }
        );
      }
    } catch {
      setError(`Failed to load type localities for ${t.rank} "${t.name}"`);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Clear selection and restore global view ───────────────────────────────
  const clearAll = useCallback(() => {
    setSelected(null);
    setSelectedTaxon(null);
    selectedRef.current = null;
    setQuery("");
    setSuggestions([]);
    setTaxonSuggestions([]);
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
  const typeLocLayerLabel = selectedTaxon
    ? `Type localities — ${selectedTaxon.name} (${typeLocalityCount})`
    : selected && !showAllTypeLocalities
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
          <label className="section-label">Search</label>

          {/* Rank selector */}
          <div className="rank-selector">
            {(["species", "genus", "family"] as const).map((r) => (
              <button
                key={r}
                className={`rank-btn${rank === r ? " rank-btn-active" : ""}`}
                onClick={() => {
                  if (rank === r) return;
                  setRank(r);
                  setQuery("");
                  setSuggestions([]);
                  setTaxonSuggestions([]);
                  setError(null);
                  if (selected || selectedTaxon) clearAll();
                }}
              >
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>

          <div className="search-wrap">
            <div className="search-input-row">
              <input
                className="search-input"
                type="text"
                placeholder={
                  rank === "species"
                    ? "e.g. Ursus arctos, galago…"
                    : rank === "genus"
                    ? "e.g. Ursus, Galago…"
                    : "e.g. Ursidae, Galagidae…"
                }
                value={query}
                onChange={(e) => handleQueryChange(e.target.value, rank)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && rank === "species") handleSearchSubmit(query);
                }}
              />
              {(selected || selectedTaxon) && (
                <button className="clear-btn" onClick={clearAll} title="Clear selection">
                  ×
                </button>
              )}
            </div>

            {/* Species autocomplete */}
            {rank === "species" && suggestions.length > 0 && (
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

            {/* Genus / family autocomplete */}
            {rank !== "species" && taxonSuggestions.length > 0 && (
              <ul className="suggestions">
                {taxonSuggestions.map((t) => (
                  <li key={`${t.rank}-${t.name}`} onClick={() => selectTaxon(t)}>
                    <span className="sug-sci">{t.name}</span>
                    <span className="sug-common">{t.species_count} species</span>
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

        {/* Taxon (genus / family) summary card */}
        {selectedTaxon && (
          <section className="section species-card">
            <div className="taxon-rank-label">
              {selectedTaxon.rank === "genus" ? "Genus" : "Family"}
            </div>
            <div className="species-sci">{selectedTaxon.name}</div>
            <div className="taxon-species-count">
              {selectedTaxon.species_count} species
            </div>
            <p className="type-locality-text">
              Showing type localities for all species in this {selectedTaxon.rank}.
            </p>
            <div className="occ-status">
              <span className="occ-empty">
                GBIF occurrences are loaded per species — select a species to import.
              </span>
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

          {/* "Show all" sub-toggle — only in single-species mode */}
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

          {/* Help text when in single-species mode */}
          {selected && !showAllTypeLocalities && (
            <p className="type-loc-help">
              Type locality = holotype collection site. One per accepted species in MDD.
            </p>
          )}
          {/* Taxon hint */}
          {selectedTaxon && (
            <p className="layer-hint">
              Type localities for all species in {selectedTaxon.rank} {selectedTaxon.name} · coloured by IUCN status
            </p>
          )}
          {/* Global hint (nothing selected) */}
          {!selected && !selectedTaxon && (
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
