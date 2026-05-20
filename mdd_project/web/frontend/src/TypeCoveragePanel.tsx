import { useEffect, useMemo, useState } from "react";

const API = "/api";

interface CoverageSummary {
  total_species: number;
  with_type_voucher: number;
  with_type_locality_text: number;
  geocoded: number;
  voucher_with_museum_match: number;
  voucher_unmatched_museum: number;
  voucher_geocoded: number;
  voucher_missing_geolocation: number;
  estimated_on_map?: number;
}

interface CoverageMuseum {
  abbreviation: string;
  full_name: string | null;
  city_and_country: string | null;
  country: string | null;
  with_type_voucher: number;
  geocoded: number;
  missing_geolocation: number;
}

interface CoverageCountry {
  country: string;
  museum_count: number;
  with_type_voucher: number;
  geocoded: number;
  missing_geolocation: number;
}

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

function pct(geocoded: number, total: number): number {
  return total > 0 ? Math.round((geocoded / total) * 100) : 0;
}

function StatBar({ geocoded, total }: { geocoded: number; total: number }) {
  const p = pct(geocoded, total);
  return (
    <div className="coverage-bar-wrap" aria-hidden>
      <div className="coverage-bar">
        <div className="coverage-bar-fill" style={{ width: `${p}%` }} />
      </div>
      <span className="coverage-bar-label">{p}% on map</span>
    </div>
  );
}

export interface TypeCoveragePanelProps {
  country: string;
  museum: string;
  onCountryChange: (country: string) => void;
  onMuseumChange: (museum: string) => void;
}

export default function TypeCoveragePanel({
  country,
  museum,
  onCountryChange,
  onMuseumChange,
}: TypeCoveragePanelProps) {
  const [summary, setSummary] = useState<CoverageSummary | null>(null);
  const [countries, setCountries] = useState<CoverageCountry[]>([]);
  const [museums, setMuseums] = useState<CoverageMuseum[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchJson<CoverageSummary>(`${API}/type-localities/coverage/summary`),
      fetchJson<CoverageCountry[]>(`${API}/type-localities/coverage/countries`),
    ])
      .then(([s, c]) => {
        setSummary(s);
        setCountries(c);
      })
      .catch(() => setError("Could not load coverage statistics."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const url = country
      ? `${API}/type-localities/coverage/museums?country=${encodeURIComponent(country)}`
      : `${API}/type-localities/coverage/museums`;
    fetchJson<CoverageMuseum[]>(url)
      .then(setMuseums)
      .catch(() => setMuseums([]));
    onMuseumChange("");
  }, [country, onMuseumChange]);

  const selectedCountry = useMemo(
    () => countries.find((c) => c.country === country) ?? null,
    [countries, country]
  );

  const selectedMuseum = useMemo(
    () => museums.find((m) => m.abbreviation === museum) ?? null,
    [museums, museum]
  );

  const selectionStats = selectedMuseum ?? selectedCountry;

  const exportUrl = museum
    ? `${API}/type-localities/coverage/export?museum=${encodeURIComponent(museum)}`
    : country
      ? `${API}/type-localities/coverage/export?country=${encodeURIComponent(country)}`
      : null;

  return (
    <section className="section coverage-section">
      <label className="section-label">Type specimen coverage</label>

      {loading && <p className="coverage-hint">Loading statistics…</p>}
      {error && <p className="error-msg">{error}</p>}

      {summary && !loading && (
        <>
          <div className="coverage-summary">
            <div className="coverage-stat">
              <span className="coverage-stat-n">{summary.with_type_voucher.toLocaleString()}</span>
              <span className="coverage-stat-l">with type voucher</span>
            </div>
            <div className="coverage-stat">
              <span className="coverage-stat-n">{summary.geocoded.toLocaleString()}</span>
              <span className="coverage-stat-l">geocoded on map</span>
            </div>
            <div className="coverage-stat coverage-stat-warn">
              <span className="coverage-stat-n">
                {summary.voucher_missing_geolocation.toLocaleString()}
              </span>
              <span className="coverage-stat-l">voucher, no coordinates</span>
            </div>
            {(summary.estimated_on_map ?? 0) > 0 && (
              <div className="coverage-stat coverage-stat-estimated">
                <span className="coverage-stat-n">
                  {summary.estimated_on_map!.toLocaleString()}
                </span>
                <span className="coverage-stat-l">estimated (review)</span>
              </div>
            )}
          </div>
          <StatBar geocoded={summary.geocoded} total={summary.with_type_voucher} />
          <p className="coverage-hint">
            {summary.total_species.toLocaleString()} accepted species in MDD v2.4 ·{" "}
            {summary.voucher_with_museum_match.toLocaleString()} vouchers matched to a museum
            {(summary.estimated_on_map ?? 0) > 0
              ? ` · ${summary.estimated_on_map!.toLocaleString()} estimated review points available in map layer`
              : ""}
          </p>

          <div className="coverage-filters">
            <label className="coverage-filter-label">
              Museum country
              <select
                className="coverage-select"
                value={country}
                onChange={(e) => onCountryChange(e.target.value)}
              >
                <option value="">All countries</option>
                {countries.map((c) => (
                  <option key={c.country} value={c.country}>
                    {c.country} ({c.with_type_voucher.toLocaleString()} vouchers)
                  </option>
                ))}
              </select>
            </label>

            <label className="coverage-filter-label">
              Museum
              <select
                className="coverage-select"
                value={museum}
                onChange={(e) => onMuseumChange(e.target.value)}
              >
                <option value="">Select museum…</option>
                {museums.map((m) => (
                  <option key={m.abbreviation} value={m.abbreviation}>
                    {m.abbreviation} — {m.full_name ?? m.abbreviation} (
                    {m.missing_geolocation.toLocaleString()} missing coords)
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selectionStats && (
            <div className="coverage-selection">
              <h4 className="coverage-selection-title">
                {selectedMuseum
                  ? `${selectedMuseum.abbreviation} · ${selectedMuseum.full_name ?? ""}`
                  : selectedCountry?.country}
              </h4>
              {selectedMuseum?.city_and_country && (
                <p className="coverage-selection-loc">{selectedMuseum.city_and_country}</p>
              )}
              <dl className="coverage-dl">
                <dt>Type vouchers</dt>
                <dd>{selectionStats.with_type_voucher.toLocaleString()}</dd>
                <dt>On map (geocoded)</dt>
                <dd>{selectionStats.geocoded.toLocaleString()}</dd>
                <dt>Missing coordinates</dt>
                <dd className="coverage-missing">
                  {selectionStats.missing_geolocation.toLocaleString()}
                </dd>
                {selectedCountry && !selectedMuseum && (
                  <>
                    <dt>Museums</dt>
                    <dd>{selectedCountry.museum_count.toLocaleString()}</dd>
                  </>
                )}
              </dl>
              <StatBar
                geocoded={selectionStats.geocoded}
                total={selectionStats.with_type_voucher}
              />
            </div>
          )}

          {(country || museum) && (
            <p className="coverage-hint coverage-map-hint">
              Map shows geocoded type localities for this filter only.
            </p>
          )}

          {exportUrl ? (
            <a className="coverage-export-btn" href={exportUrl} download>
              Download CSV — species missing coordinates
              {museum ? ` (${museum})` : country ? ` (${country})` : ""}
            </a>
          ) : (
            <p className="coverage-hint">
              Select a country or museum to export a list of species whose type localities are
              not geocoded in MDD (for curation / coordinate updates).
            </p>
          )}
        </>
      )}
    </section>
  );
}

