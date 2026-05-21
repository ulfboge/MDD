import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, {
  type Map,
  type GeoJSONSource,
  type MapMouseEvent,
  type MapGeoJSONFeature,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./App.css";
import TypeCoveragePanel from "./TypeCoveragePanel";

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
const IUCN_LABEL: Record<string, string> = {
  LC: "Livskraftig",
  NT: "Nära hotad",
  VU: "Sårbar",
  EN: "Starkt hotad",
  CR: "Akut hotad",
  EW: "Utdöd i vilt tillstånd",
  EX: "Utdöd",
  DD: "Kunskapsbrist",
};
function iucnColor(status: string | null): string {
  return IUCN_COLOR[status ?? ""] ?? "#4f9cf9";
}
function iucnRedListUrl(sciNameSpace: string): string {
  return `https://www.iucnredlist.org/search?query=${encodeURIComponent(sciNameSpace)}`;
}
function voucherUriLabel(url: string): string {
  const host = url.toLowerCase();
  if (host.includes("portal.vertnet.org")) return "VertNet";
  if (host.includes("idigbio.org")) return "iDigBio";
  if (host.includes("gbif.org")) return "GBIF";
  if (host.includes("data.nhm.ac.uk")) return "NHM Data Portal";
  return "Samlingskatalog";
}
function parseVoucherUris(raw: string | null): string[] {
  if (!raw) return [];
  return raw
    .split("|")
    .map((part) => part.trim())
    .filter((part) => part.startsWith("http"));
}
function voucherUriLinksHtml(raw: string | null): string {
  const uris = parseVoucherUris(raw);
  if (!uris.length) return "";
  const links = uris
    .slice(0, 4)
    .map(
      (uri) =>
        `<a class="popup-link" href="${escapeHtml(uri)}" target="_blank" rel="noopener noreferrer">${escapeHtml(voucherUriLabel(uri))} ↗</a>`
    )
    .join("");
  return `<footer class="popup-footer popup-footer-links">${links}</footer>`;
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
    p.type_voucher_uris != null && String(p.type_voucher_uris).trim() !== ""
      ? String(p.type_voucher_uris).trim()
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
      ${uri ? voucherUriLinksHtml(uri) : ""}
    </div>`;
}

function estimatedLocalityPopupHtml(p: Record<string, string | null>): string {
  const confidence = p.geocode_confidence ? escapeHtml(String(p.geocode_confidence)) : "unknown";
  const uncertainty = p.coordinate_uncertainty_m
    ? `${escapeHtml(String(p.coordinate_uncertainty_m))} m`
    : "—";
  const base = typeLocalityPopupHtml(p);
  return base.replace(
    '<div class="popup-content popup-content--type-loc">',
    `<div class="popup-content popup-content--type-loc popup-content--estimated">
      <p class="popup-estimated-banner"><strong>Estimated location</strong> — not official MDD data. Confidence: ${confidence}; uncertainty ± ${uncertainty}.</p>`
  );
}

// ---------------------------------------------------------------------------
// Map source / layer IDs
// ---------------------------------------------------------------------------
const SRC_TYPE_LOC = "type-localities";
const SRC_ESTIMATED = "estimated-type-localities";
const SRC_OCCURRENCES = "occurrences";
const LYR_TYPE_LOC = "type-localities-circle";
const LYR_ESTIMATED = "estimated-type-localities-circle";
const LYR_OCCURRENCES = "occurrences-circle";
const GBIF_COLOR = "#ff7043";

// Neutral light basemap — keeps IUCN / GBIF colours readable vs colourful OSM
const BASEMAP_TILES =
  "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png";
const BASEMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

function fitMapToTypeLocFc(map: Map, fc: TypeLocFC) {
  const coords = (fc.features as Array<{ geometry: { coordinates: [number, number] } }>)
    .map((f) => f.geometry.coordinates)
    .filter((c) => c && c.length === 2);
  if (!coords.length) return;
  const lngs = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  map.fitBounds(
    [
      [Math.min(...lngs), Math.min(...lats)],
      [Math.max(...lngs), Math.max(...lats)],
    ],
    { padding: 80, maxZoom: 8, duration: 1200 }
  );
}

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
  const allEstimatedLocCacheRef = useRef<TypeLocFC | null>(null);
  // Mirror of `selected` in a ref so effects can read it without stale closures.
  const selectedRef = useRef<SpeciesRecord | null>(null);
  const selectedTaxonRef = useRef<TaxonResult | null>(null);
  const showAllTypeLocalitiesRef = useRef(false);

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
  const [showEstimatedLocalities, setShowEstimatedLocalities] = useState(false);
  const [showOccurrences, setShowOccurrences] = useState(true);
  const [typeLocalityCount, setTypeLocalityCount] = useState<number>(0);
  const [estimatedLocalityCount, setEstimatedLocalityCount] = useState<number>(0);
  // When a species is selected this is false (show 1 point); user can toggle
  // to true to temporarily display all ~1,941 MDD type localities.
  const [showAllTypeLocalities, setShowAllTypeLocalities] = useState(false);
  const [coverageCountry, setCoverageCountry] = useState("");
  const [coverageMuseum, setCoverageMuseum] = useState("");
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    showAllTypeLocalitiesRef.current = showAllTypeLocalities;
  }, [showAllTypeLocalities]);

  useEffect(() => {
    selectedTaxonRef.current = selectedTaxon;
  }, [selectedTaxon]);

  const shouldShowGlobalTypeLocalities = useCallback(() => {
    if (selectedTaxonRef.current) return false;
    if (selectedRef.current && !showAllTypeLocalitiesRef.current) return false;
    return true;
  }, []);

  const applyTypeLocalitiesToMap = useCallback((fc: TypeLocFC) => {
    const map = mapRef.current;
    const source = map?.getSource(SRC_TYPE_LOC) as GeoJSONSource | undefined;
    if (!source) return false;
    source.setData(fc as Parameters<GeoJSONSource["setData"]>[0]);
    setTypeLocalityCount(fc.meta.count);
    return true;
  }, []);

  const applyTypeLocalitiesIfAllowed = useCallback(
    (fc: TypeLocFC) => {
      if (!shouldShowGlobalTypeLocalities()) return false;
      return applyTypeLocalitiesToMap(fc);
    },
    [applyTypeLocalitiesToMap, shouldShowGlobalTypeLocalities]
  );

  const fetchAllTypeLocalities = useCallback(async (): Promise<TypeLocFC> => {
    const cached = allTypeLocCacheRef.current;
    if (cached) return cached;
    const fc = await fetchJson<TypeLocFC>(`${API}/type-localities?limit=10000`);
    allTypeLocCacheRef.current = fc;
    return fc;
  }, []);

  const applyEstimatedLocalitiesToMap = useCallback((fc: TypeLocFC) => {
    const map = mapRef.current;
    const source = map?.getSource(SRC_ESTIMATED) as GeoJSONSource | undefined;
    if (!source) return false;
    source.setData(fc as Parameters<GeoJSONSource["setData"]>[0]);
    setEstimatedLocalityCount(fc.meta.count);
    return true;
  }, []);

  const fetchAllEstimatedLocalities = useCallback(async (): Promise<TypeLocFC> => {
    const cached = allEstimatedLocCacheRef.current;
    if (cached) return cached;
    const fc = await fetchJson<TypeLocFC>(`${API}/type-localities/estimated?limit=20000`);
    allEstimatedLocCacheRef.current = fc;
    return fc;
  }, []);

  const loadOccurrencesForSpecies = useCallback(async (sciName: string) => {
    const map = mapRef.current;
    const source = map?.getSource(SRC_OCCURRENCES) as GeoJSONSource | undefined;
    if (!map || !mapReady || !source) return;

    setLoadingOcc(true);
    try {
      const fc = await fetchJson<{
        features: object[];
        meta: OccurrenceMeta;
        type: string;
      }>(`${API}/occurrences/${encodeURIComponent(sciName)}`);

      source.setData({
        type: "FeatureCollection",
        features: fc.features,
      } as Parameters<GeoJSONSource["setData"]>[0]);
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
    } catch (err) {
      console.error("Failed to load GBIF occurrences:", err);
      source.setData({ type: "FeatureCollection", features: [] });
      setOccurrenceMeta({ count: 0, limit: 500 });
    } finally {
      setLoadingOcc(false);
    }
  }, [mapReady]);

  const loadEstimatedLocalitiesForView = useCallback(async () => {
    const map = mapRef.current;
    if (!map || !showEstimatedLocalities) return;

    const sp = selectedRef.current;
    const taxon = selectedTaxonRef.current;

    if (sp && !showAllTypeLocalitiesRef.current) {
      try {
        const fc = await fetchJson<TypeLocFC>(
          `${API}/type-localities/estimated?species=${encodeURIComponent(sp.sci_name)}&limit=5`
        );
        applyEstimatedLocalitiesToMap(fc);
      } catch (err) {
        console.error("Failed to load estimated type localities for species:", err);
      }
      return;
    }

    if (taxon) {
      const paramKey = taxon.rank === "genus" ? "genus" : "family";
      try {
        const fc = await fetchJson<TypeLocFC>(
          `${API}/type-localities/estimated?${paramKey}=${encodeURIComponent(taxon.name)}&limit=2000`
        );
        applyEstimatedLocalitiesToMap(fc);
      } catch (err) {
        console.error("Failed to load estimated type localities for taxon:", err);
      }
      return;
    }

    const hasFilter = Boolean(coverageMuseum || coverageCountry);
    if (!hasFilter) {
      try {
        const fc = await fetchAllEstimatedLocalities();
        applyEstimatedLocalitiesToMap(fc);
      } catch (err) {
        console.error("Failed to load estimated type localities:", err);
      }
      return;
    }

    const params = new URLSearchParams({ limit: "20000" });
    if (coverageMuseum) params.set("museum", coverageMuseum);
    else if (coverageCountry) params.set("country", coverageCountry);

    try {
      const fc = await fetchJson<TypeLocFC>(`${API}/type-localities/estimated?${params}`);
      applyEstimatedLocalitiesToMap(fc);
    } catch (err) {
      console.error("Failed to load filtered estimated type localities:", err);
    }
  }, [
    applyEstimatedLocalitiesToMap,
    coverageCountry,
    coverageMuseum,
    fetchAllEstimatedLocalities,
    showEstimatedLocalities,
  ]);

  const fetchAllTypeLocalitiesRef = useRef(fetchAllTypeLocalities);
  const applyTypeLocalitiesToMapRef = useRef(applyTypeLocalitiesToMap);

  useEffect(() => {
    fetchAllTypeLocalitiesRef.current = fetchAllTypeLocalities;
  }, [fetchAllTypeLocalities]);

  useEffect(() => {
    applyTypeLocalitiesToMapRef.current = applyTypeLocalitiesToMap;
  }, [applyTypeLocalitiesToMap]);

  const loadTypeLocalitiesForView = useCallback(async () => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedTaxon) return;
    if (selectedRef.current && !showAllTypeLocalities) return;

    const hasFilter = Boolean(coverageMuseum || coverageCountry);
    if (!hasFilter) {
      try {
        const fc = await fetchAllTypeLocalities();
        applyTypeLocalitiesToMap(fc);
      } catch (err) {
        console.error("Failed to load type localities:", err);
      }
      return;
    }

    const params = new URLSearchParams({ limit: "10000" });
    if (coverageMuseum) params.set("museum", coverageMuseum);
    else if (coverageCountry) params.set("country", coverageCountry);

    try {
      const fc = await fetchJson<TypeLocFC>(`${API}/type-localities?${params}`);
      applyTypeLocalitiesToMap(fc);
      fitMapToTypeLocFc(map, fc);
    } catch (err) {
      console.error("Failed to load filtered type localities:", err);
    }
  }, [
    applyTypeLocalitiesToMap,
    coverageCountry,
    coverageMuseum,
    fetchAllTypeLocalities,
    selectedTaxon,
    showAllTypeLocalities,
  ]);

  // Warm the cache early so startup can paint points as soon as the map source exists.
  useEffect(() => {
    void fetchAllTypeLocalities()
      .then((fc) => {
        applyTypeLocalitiesIfAllowed(fc);
      })
      .catch((err) => {
        console.error("Failed to prefetch type localities:", err);
      });
  }, [applyTypeLocalitiesIfAllowed, fetchAllTypeLocalities]);

  // If prefetch finished before the map source existed, apply once the map is ready.
  useEffect(() => {
    if (!mapReady) return;
    const cached = allTypeLocCacheRef.current;
    if (cached) applyTypeLocalitiesIfAllowed(cached);
  }, [applyTypeLocalitiesIfAllowed, mapReady]);

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

    const initMapDataLayers = () => {
      if (map.getSource(SRC_TYPE_LOC)) return;

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

      map.addSource(SRC_OCCURRENCES, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addSource(SRC_ESTIMATED, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: LYR_ESTIMATED,
        type: "circle",
        source: SRC_ESTIMATED,
        layout: { visibility: "none" },
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            2, 3,
            8, 6,
          ],
          "circle-color": "#d4a056",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#8a5a12",
          "circle-opacity": 0.72,
        },
      });

      // GBIF occurrences on top so they stay visible over type-locality dots
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
          "circle-color": GBIF_COLOR,
          "circle-stroke-width": 1,
          "circle-stroke-color": "rgba(0,0,0,0.5)",
          "circle-opacity": 0.85,
        },
      });

      setMapReady(true);

      const cached = allTypeLocCacheRef.current;
      if (cached) {
        if (shouldShowGlobalTypeLocalities()) {
          applyTypeLocalitiesToMapRef.current(cached);
        }
      } else {
        void fetchAllTypeLocalitiesRef.current()
          .then((fc) => {
            if (shouldShowGlobalTypeLocalities()) {
              applyTypeLocalitiesToMapRef.current(fc);
            }
          })
          .catch((err) => {
            console.error("Failed to load initial type localities:", err);
          });
      }

      // ── Pointer cursor on hover ───────────────────────────────────────────
      for (const lyr of [LYR_TYPE_LOC, LYR_ESTIMATED, LYR_OCCURRENCES]) {
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

      map.on("click", LYR_ESTIMATED, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as Record<string, string | null>;
        popup.setLngLat(e.lngLat).setHTML(estimatedLocalityPopupHtml(p)).addTo(map);
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
    };

    // Inline styles can finish loading before this listener is attached.
    if (map.isStyleLoaded()) {
      initMapDataLayers();
    } else {
      map.once("load", initMapDataLayers);
    }

    mapRef.current = map;
    return () => {
      setMapReady(false);
      allTypeLocCacheRef.current = null;
      allEstimatedLocCacheRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const source = map?.getSource(SRC_OCCURRENCES) as GeoJSONSource | undefined;
    if (!mapReady || !source) return;

    if (!selected) {
      source.setData({ type: "FeatureCollection", features: [] });
      setOccurrenceMeta(null);
      return;
    }

    void loadOccurrencesForSpecies(selected.sci_name);
  }, [loadOccurrencesForSpecies, mapReady, selected]);

  // ── Layer visibility toggles ──────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.setLayoutProperty(LYR_TYPE_LOC, "visibility", showTypeLocalities ? "visible" : "none");
  }, [mapReady, showTypeLocalities]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.setLayoutProperty(LYR_OCCURRENCES, "visibility", showOccurrences ? "visible" : "none");
  }, [mapReady, showOccurrences]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.setLayoutProperty(
      LYR_ESTIMATED,
      "visibility",
      showEstimatedLocalities ? "visible" : "none"
    );
    if (showEstimatedLocalities) {
      void loadEstimatedLocalitiesForView();
    }
  }, [loadEstimatedLocalitiesForView, mapReady, showEstimatedLocalities]);

  useEffect(() => {
    allEstimatedLocCacheRef.current = null;
    if (showEstimatedLocalities) {
      void loadEstimatedLocalitiesForView();
    }
  }, [coverageCountry, coverageMuseum, loadEstimatedLocalitiesForView, showEstimatedLocalities]);

  // ── Coverage country/museum filter → map points ───────────────────────────
  useEffect(() => {
    if (!mapReady) return;
    loadTypeLocalitiesForView();
    void loadEstimatedLocalitiesForView();
  }, [mapReady, loadTypeLocalitiesForView, loadEstimatedLocalitiesForView, selected]);

  // ── Toggle: show all MDD type localities vs. selected-species only ─────────
  useEffect(() => {
    if (!mapReady) return;

    if (showAllTypeLocalities) {
      void fetchAllTypeLocalities()
        .then((fc) => {
          applyTypeLocalitiesToMap(fc);
        })
        .catch(console.error);
      return;
    }

    // Revert to species-only view — use ref to avoid stale closure over `selected`
    const sp = selectedRef.current;
    if (sp) {
      fetchJson<TypeLocFC>(
        `${API}/type-localities?species=${encodeURIComponent(sp.sci_name)}&limit=1`
      )
        .then((fc) => {
          applyTypeLocalitiesToMap(fc);
        })
        .catch(console.error);
      return;
    }

    if (!selectedTaxon) {
      void loadTypeLocalitiesForView();
    }
  }, [applyTypeLocalitiesToMap, fetchAllTypeLocalities, loadTypeLocalitiesForView, mapReady, showAllTypeLocalities]);

  // ── Search (species / genus / family) ────────────────────────────────────
  const handleQueryChange = useCallback(async (value: string, currentRank: Rank) => {
    setQuery(value);
    setError(null);
    setSuggestions([]);
    setTaxonSuggestions([]);
    if (value.length < 2) return;
    try {
      if (currentRank === "species") {
        const results = await fetchJson<SpeciesRecord[]>(
          `${API}/species?q=${encodeURIComponent(value)}&limit=15`
        );
        setSuggestions(results);
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
    selectedTaxonRef.current = null;
    setSuggestions([]);
    setTaxonSuggestions([]);
    setQuery(sp.sci_name_space ?? sp.sci_name);
    setError(null);
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
  }, []);

  // ── Select a genus or family — load all member type localities ───────────
  const selectTaxon = useCallback(async (t: TaxonResult) => {
    setSelectedTaxon(t);
    setSelected(null);
    selectedRef.current = null;
    selectedTaxonRef.current = t;
    setSuggestions([]);
    setTaxonSuggestions([]);
    setQuery(t.name);
    setError(null);
    setShowAllTypeLocalities(false);

    const map = mapRef.current;
    if (!map) return;

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
      fitMapToTypeLocFc(map, fc);
    } catch {
      setError(`Failed to load type localities for ${t.rank} "${t.name}"`);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Clear selection and restore global view ───────────────────────────────
  const clearAll = useCallback(() => {
    setSelected(null);
    setSelectedTaxon(null);
    selectedRef.current = null;
    selectedTaxonRef.current = null;
    setQuery("");
    setSuggestions([]);
    setTaxonSuggestions([]);
    setShowAllTypeLocalities(false);
    setError(null);

    loadTypeLocalitiesForView();
  }, [loadTypeLocalitiesForView]);

  // ── Derived display values ────────────────────────────────────────────────
  const typeLocLayerLabel = selectedTaxon
    ? `Type localities — ${selectedTaxon.name} (${typeLocalityCount})`
    : selected && !showAllTypeLocalities
    ? "Type locality (selected species)"
    : coverageMuseum
    ? `Type localities — ${coverageMuseum} (${typeLocalityCount})`
    : coverageCountry
    ? `Type localities — ${coverageCountry} (${typeLocalityCount})`
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
              <div className="iucn-row">
                <div
                  className="iucn-badge"
                  style={{ background: iucnColor(selected.iucn_status) }}
                >
                  {selected.iucn_status}
                  {IUCN_LABEL[selected.iucn_status]
                    ? ` · ${IUCN_LABEL[selected.iucn_status]}`
                    : ""}
                </div>
                <a
                  className="iucn-link"
                  href={iucnRedListUrl(selected.sci_name_space ?? selected.sci_name.replace(/_/g, " "))}
                  target="_blank"
                  rel="noreferrer"
                >
                  IUCN Red List ↗
                </a>
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

        <TypeCoveragePanel
          country={coverageCountry}
          museum={coverageMuseum}
          onCountryChange={setCoverageCountry}
          onMuseumChange={setCoverageMuseum}
        />

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
              Map shows only the selected species unless you enable “Show all MDD type localities”.
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

          <div className="layer-row" style={{ marginTop: 8 }}>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showEstimatedLocalities}
                onChange={(e) => setShowEstimatedLocalities(e.target.checked)}
              />
              <span className="dot dot-estimated" style={{ background: "#d4a056", border: "2px solid #8a5a12" }} />
              Estimated type localities
            </label>
            {showEstimatedLocalities && (
              <span className="layer-count">{estimatedLocalityCount.toLocaleString()}</span>
            )}
          </div>
          {showEstimatedLocalities && (
            <p className="layer-hint layer-hint-estimated">
              Review-only estimates from type locality text — not official MDD or museum coordinates.
            </p>
          )}

          {/* GBIF occurrences row */}
          <div className="layer-row" style={{ marginTop: selected ? 8 : 0 }}>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showOccurrences}
                onChange={(e) => setShowOccurrences(e.target.checked)}
              />
              <span className="dot" style={{ background: GBIF_COLOR }} />
              GBIF occurrences
            </label>
            {selected && occurrenceMeta && (
              <span className="layer-count">{occurrenceMeta.count.toLocaleString()}</span>
            )}
          </div>
          <p className="layer-hint">
            {!selected
              ? "Select a species to load GBIF occurrence dots (data must be imported first)."
              : loadingOcc
              ? "Loading GBIF occurrences for the selected species…"
              : occurrenceMeta && occurrenceMeta.count > 0
              ? "Orange dots show GBIF sighting and specimen records for the selected species."
              : "No GBIF records in the local database for this species yet."}
          </p>
          {selected && showEstimatedLocalities && (
            <p className="layer-hint layer-hint-estimated">
              Estimated layer is filtered to the selected species only.
            </p>
          )}
        </section>

        {/* About these layers — collapsible explainer (Swedish) */}
        <section className="section">
          <details className="about-layers">
            <summary className="about-summary">Om datalagren</summary>
            <div className="about-body">
              <p>
                <strong>MDD</strong> (Mammal Diversity Database) är en global taxonomisk
                referensdatabas för däggdjur — inte en museumskatalog. Den innehåller
                accepterade artnamn, synonymer, typmaterial och typ-lokaliteter från
                vetenskaplig litteratur. Av ~14&nbsp;000 arter har ungefär 1&nbsp;941
                geokodade typ-lokaliteter i MDD v2.4; resten har bara textbeskrivning.
              </p>
              <p>
                <strong>Uppskattade typ-lokaliteter</strong> (valfritt lager) är
                maskinassisterade gissningar för arter utan officiella MDD-koordinater.
                De är granskningsobjekt — inte MDD- eller museidata. Använd dem som
                ledtrådar, inte som facit.
              </p>
              <p>
                <strong>GBIF-förekomster</strong> är oberoende observations- och
                samlingsposter (museer, citizen science m.m.) via GBIF. En art kan sakna
                typ-lokalitet men ha många GBIF-punkter, eller tvärtom. Det är medvetet
                separata lager.
              </p>
              <p>
                <strong>IUCN-status</strong> (färg på typ-lokaliteter) kommer från MDD:s
                inbäddade rödlisteklassificering per art — inte från IUCN:s kartlager.
                Klicka på en art för länk till IUCN Red List.
              </p>
              <p>
                <strong>VertNet / iDigBio</strong> används här bara som kompletterande
                kataloglänkar till typmaterial (voucher-URI), när MDD har sådan
                information. De ersätter inte MDD-taxonomin och ger inte full
                samlingsöversikt.
              </p>
            </div>
          </details>
        </section>

        {/* IUCN legend */}
        <section className="section">
          <label className="section-label">IUCN (typ-lokaliteter)</label>
          <div className="legend">
            {Object.entries(IUCN_COLOR).map(([code, color]) => (
              <div key={code} className="legend-row">
                <span className="legend-dot" style={{ background: color }} />
                <span>
                  {code}
                  {IUCN_LABEL[code] ? ` · ${IUCN_LABEL[code]}` : ""}
                </span>
              </div>
            ))}
          </div>
        </section>

        <footer className="sidebar-footer">
          Data:{" "}
          <a href="https://www.mammaldiversity.org/" target="_blank" rel="noreferrer">
            MDD v2.4
          </a>
          {" · "}
          <a href="https://www.iucnredlist.org/" target="_blank" rel="noreferrer">
            IUCN Red List
          </a>
          {" · "}
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
