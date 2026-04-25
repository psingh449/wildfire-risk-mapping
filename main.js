const MAP_PANELS = [
    { panelId: "map-panel-eal", metric: "eal_norm" },
    { panelId: "map-panel-risk", metric: "risk_score" },
    { panelId: "map-panel-hazard", metric: "hazard_score" },
    { panelId: "map-panel-exposure", metric: "exposure_score" },
    { panelId: "map-panel-vulnerability", metric: "vulnerability_score" },
    { panelId: "map-panel-resilience", metric: "resilience_score" },
];

// Detail text under each map (shown only when "Detail" is checked).
// HTML is authored here so we can mix bullets + inline <code> + bold/colored section headers.
const PANEL_DETAIL_HTML = {
    eal_norm: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-el"><b>Expected Annual Loss is our “economic consequence” view:</b></span> how much $ loss we expect in a typical year for each block group</p>
        <div class="map-calc__subhead"><b>Calculation</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Two numbers exist: <code class="map-calc__inline">eal</code> (USD) and <code class="map-calc__inline">eal_norm</code> (0–1).</li>
            <li class="map-calc__item">This panel maps <code class="map-calc__inline">eal_norm</code> so the choropleth has contrast even when dollar values span huge ranges.</li>
            <li class="map-calc__item">Interpretation: darker = higher expected annual loss (relative within the run), not “guaranteed loss.”</li>
        </ul>
        <div class="map-calc__subhead"><b>How Expected Annual Loss built</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">compute overall Risk on 0–1.</li>
            <li class="map-calc__item">estimate “value at stake” (<code class="map-calc__inline">exposure_building_value</code>).</li>
            <li class="map-calc__item">multiply: <code class="map-calc__inline">eal = risk_score × exposure_building_value</code></li>
            <li class="map-calc__item">Then rescale for the map: <code class="map-calc__inline">eal_norm = (eal − min) / (max − min)</code></li>
            <li class="map-calc__item"><b>Why normalize?</b> Without it, almost every block group would look the same color when a few very-large-dollar areas dominate the scale.</li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON fields: <code class="map-calc__inline">eal</code>, <code class="map-calc__inline">eal_norm</code>, <code class="map-calc__inline">exposure_building_value</code>, <code class="map-calc__inline">risk_score</code></li>
            <li class="map-calc__item">Primary implementation: <code class="map-calc__inline">src/models/risk_model.py</code> (EAL + normalization)</li>
            <li class="map-calc__item">Frontend metric key: <code class="map-calc__inline">eal_norm</code> (see <code class="map-calc__inline">main.js → MAP_PANELS</code>)</li>
            <li class="map-calc__item">Tooltip formatting: <code class="map-calc__inline">_formatValue</code>, <code class="map-calc__inline">_debugTagEalFamily</code></li>
        </ul>
    `,
    risk_score: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-risk"><b>Risk is the “overall ranking” score:</b></span> where is wildfire risk comparatively higher inside a county?</p>
        <div class="map-calc__subhead"><b>Conceptual model</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Hazard = how fire-prone the place is.</li>
            <li class="map-calc__item">Exposure = how many people/structures are in the way.</li>
            <li class="map-calc__item">Vulnerability = who may be less able to cope/evacuate.</li>
            <li class="map-calc__item">Resilience = response/recovery capacity (help close by).</li>
        </ul>
        <div class="map-calc__subhead"><b>The formula (why it behaves this way)</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item"><code class="map-calc__inline">risk_score = hazard_score × exposure_score × vulnerability_score × (1 − resilience_score)</code></li>
            <li class="map-calc__item">Multiplication matters: if any component is near 0, overall risk shrinks fast.</li>
            <li class="map-calc__item">Resilience reduces risk: bigger resilience ⇒ bigger <code class="map-calc__inline">(1 − resilience)</code> reduction.</li>
            <li class="map-calc__item">Practical consequence: values can be very small (e.g., <code class="map-calc__inline">0.003</code>), especially when all components are fractions.</li>
        </ul>
        <div class="map-calc__subhead"><b>How to read the colors</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">The number is always the same raw value (<code class="map-calc__inline">risk_score</code>).</li>
            <li class="map-calc__item">The colors are stretched within the selected county so tiny-but-real differences remain visible.</li>
            <li class="map-calc__item">This is visual scaling only (no additional <code class="map-calc__inline">risk_score_norm</code> column is created).</li>
            <li class="map-calc__item">If you switch counties, the Risk colors can shift because the min/max window changes — that’s expected.</li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON field: <code class="map-calc__inline">risk_score</code></li>
            <li class="map-calc__item">Depends on: <code class="map-calc__inline">hazard_score</code>, <code class="map-calc__inline">exposure_score</code>, <code class="map-calc__inline">vulnerability_score</code>, <code class="map-calc__inline">resilience_score</code></li>
            <li class="map-calc__item">Primary implementation: <code class="map-calc__inline">src/models/risk_model.py:compute_risk</code></li>
            <li class="map-calc__item">Visualization scaling: <code class="map-calc__inline">main.js:_computeDomainForMetric</code> (county-level min/max for colors)</li>
            <li class="map-calc__item"><code class="map-calc__inline">Risk (RISC)</code></li>
        </ul>
    `,
    hazard_score: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-hazard"><b>Hazard asks:</b></span> is this place physically conducive to wildfire?</p>
        <div class="map-calc__subhead"><b>Three building blocks</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Wildfire probability (<code class="map-calc__inline">hazard_wildfire</code>)</li>
            <li class="map-calc__item">Fuel / vegetation proxy (<code class="map-calc__inline">hazard_vegetation</code>)</li>
            <li class="map-calc__item">Proximity to forest-like land (<code class="map-calc__inline">hazard_forest_distance</code>)</li>
        </ul>
        <div class="map-calc__subhead"><b>Why there are “proxy” paths</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Some counties may lack the “ideal” raster-derived inputs at build time.</li>
            <li class="map-calc__item">In that case we use a proxy blend so the panel stays informative, but it is flagged as <code class="map-calc__inline">PROXY</code> in provenance.</li>
            <li class="map-calc__item">When both primary + proxy are missing, values become missing (shown as <code class="map-calc__inline">—</code>).</li>
            <li class="map-calc__item">In debug mode you’ll see tags like <code class="map-calc__inline">[src:whp]</code> vs <code class="map-calc__inline">[px:osm]</code> indicating which path fed the number.</li>
        </ul>
        <div class="map-calc__subhead"><b>Composite</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Inputs are first rescaled to 0–1 within the run for comparability.</li>
            <li class="map-calc__item">Then weighted and combined: <code class="map-calc__inline">hazard_score = Σ wᵢ × inputᵢ_norm</code></li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON fields: <code class="map-calc__inline">hazard_wildfire</code>, <code class="map-calc__inline">hazard_vegetation</code>, <code class="map-calc__inline">hazard_forest_distance</code>, <code class="map-calc__inline">hazard_score</code></li>
            <li class="map-calc__item">Data + fallbacks: <code class="map-calc__inline">src/utils/real_data.py</code> (real/proxy/missing tiers)</li>
            <li class="map-calc__item">Normalization + weighted sum: <code class="map-calc__inline">src/features/build_features.py</code></li>
        </ul>
    `,
    exposure_score: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-exposure"><b>Exposure asks:</b></span> how much is in the way if a fire happens?</p>
        <div class="map-calc__subhead"><b>What counts as “exposed” here</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">People (<code class="map-calc__inline">exposure_population</code>)</li>
            <li class="map-calc__item">Homes (<code class="map-calc__inline">exposure_housing</code>)</li>
            <li class="map-calc__item">Residential value proxy (<code class="map-calc__inline">exposure_building_value</code>)</li>
        </ul>
        <div class="map-calc__subhead"><b>Value proxy (why it’s reasonable)</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">We estimate “total residential value” as: <code class="map-calc__inline">exposure_building_value = housing_units × median_home_value</code></li>
            <li class="map-calc__item">If a local median is missing, we use a county mean so the map doesn’t collapse to zero.</li>
            <li class="map-calc__item">This is an exposure ranking tool, not a parcel-level appraisal.</li>
        </ul>
        <div class="map-calc__subhead"><b>Composite</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Population, housing, and value are normalized to 0–1 and combined with weights.</li>
            <li class="map-calc__item"><code class="map-calc__inline">exposure_score = Σ wᵢ × inputᵢ_norm</code></li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON fields: <code class="map-calc__inline">exposure_population</code>, <code class="map-calc__inline">exposure_housing</code>, <code class="map-calc__inline">exposure_building_value</code>, <code class="map-calc__inline">exposure_score</code></li>
            <li class="map-calc__item">Census + ACS joins: <code class="map-calc__inline">src/utils/real_data.py</code> (including county-mean imputation rules)</li>
            <li class="map-calc__item">Normalization + weighted sum: <code class="map-calc__inline">src/features/build_features.py</code></li>
        </ul>
    `,
    vulnerability_score: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-vulnerability"><b>Vulnerability asks:</b></span> if a fire happens, who might face a harder time responding?</p>
        <div class="map-calc__subhead"><b>The three signals</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Poverty share (<code class="map-calc__inline">vuln_poverty</code>)</li>
            <li class="map-calc__item">Older adult share (<code class="map-calc__inline">vuln_elderly</code>)</li>
            <li class="map-calc__item">Uninsured share (<code class="map-calc__inline">vuln_uninsured</code>)</li>
        </ul>
        <div class="map-calc__subhead"><b>Important direction rule (insurance)</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">We use <code class="map-calc__inline">vuln_uninsured</code> (share without health insurance) so that higher values naturally mean higher vulnerability.</li>
            <li class="map-calc__item">No inversion step is required for this component.</li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON fields: <code class="map-calc__inline">vuln_poverty</code>, <code class="map-calc__inline">vuln_elderly</code>, <code class="map-calc__inline">vuln_uninsured</code>, <code class="map-calc__inline">vulnerability_score</code></li>
            <li class="map-calc__item">ACS imports: <code class="map-calc__inline">src/utils/real_data.py</code> (pulls ACS tables and caches under <code class="map-calc__inline">data/real_cache/…</code>)</li>
            <li class="map-calc__item">Feature assembly: <code class="map-calc__inline">src/utils/real_data.py</code> (applies tract→block group assignment + provenance)</li>
            <li class="map-calc__item">Normalization + combine: <code class="map-calc__inline">src/features/build_features.py</code></li>
            <li class="map-calc__item"><code class="map-calc__inline">Vulnerability</code></li>
        </ul>
    `,
    resilience_score: `
        <p class="map-calc__lede"><span class="metric-accent metric-accent-resilience"><b>Resilience asks:</b></span> how much response capacity is nearby, and how connected is the area?</p>
        <div class="map-calc__subhead"><b>Three pieces of “capacity”</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">Vehicle access (<code class="map-calc__inline">res_vehicle_access</code>)</li>
            <li class="map-calc__item">Median household income (<code class="map-calc__inline">res_median_household_income</code>)</li>
            <li class="map-calc__item">Internet access (<code class="map-calc__inline">res_internet_access</code>)</li>
        </ul>
        <div class="map-calc__subhead"><b>How to interpret the direction</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">All three inputs are “higher = more capacity”, so no inversion is needed.</li>
            <li class="map-calc__item">They are min–max normalized within the run before forming <code class="map-calc__inline">resilience_score</code>.</li>
        </ul>
        <div class="map-calc__subhead"><b>Why it reduces risk</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">In the Risk formula, resilience enters as <code class="map-calc__inline">(1 − resilience_score)</code>.</li>
            <li class="map-calc__item">Higher resilience ⇒ smaller multiplier ⇒ lower risk.</li>
        </ul>
        <div class="map-calc__subhead"><b>Relevant code / fields</b></div>
        <ul class="map-calc__sublist">
            <li class="map-calc__item">GeoJSON fields: <code class="map-calc__inline">res_vehicle_access</code>, <code class="map-calc__inline">res_median_household_income</code>, <code class="map-calc__inline">res_internet_access</code>, <code class="map-calc__inline">resilience_score</code></li>
            <li class="map-calc__item">ACS readers: <code class="map-calc__inline">src/utils/real_data.py</code></li>
            <li class="map-calc__item">Normalization + combine: <code class="map-calc__inline">src/features/build_features.py</code></li>
        </ul>
    `
};

function populateMapCalcSections() {
    document.querySelectorAll(".map-calc").forEach((el) => {
        const metric = el.getAttribute("data-metric") || "";
        const html = PANEL_DETAIL_HTML[metric];
        el.innerHTML = html ? String(html).trim() : "";
    });
}

const BASE_STROKE = 0.65;
const HIGHLIGHT_STROKE = 3.25;

/** Stable id for linking the same block across all six maps. */
function blockKeyFromProperties(p) {
    if (!p) return "";
    if (p.block_id != null && String(p.block_id).length) return String(p.block_id);
    if (p.GEOID != null && String(p.GEOID).length) return String(p.GEOID);
    return "";
}

let hoveredBlockId = null;

function updateBlockHighlight() {
    const hid = hoveredBlockId;
    d3.selectAll(".map-cell svg.map-svg path.block-feature")
        .attr("stroke-width", function () {
            const id = this.getAttribute("data-block-id") || "";
            return hid != null && hid !== "" && id !== "" && id === hid ? HIGHLIGHT_STROKE : BASE_STROKE;
        });
}

const METRIC_COLOR_RAMPS = {
    // Option 2 palette (all six distinct)
    eal_norm: ["#E0F3F0", "#2CA89A", "#00695C"], // teal
    risk_score: ["#FFEBEE", "#EF5350", "#B71C1C"], // red
    hazard_score: ["#FFF8E1", "#FFA726", "#E65100"], // orange
    exposure_score: ["#F0F9FF", "#38BDF8", "#0369A1"], // sky
    vulnerability_score: ["#FAF5FF", "#A78BFA", "#5B21B6"], // plum
    resilience_score: ["#ECFDF5", "#34D399", "#047857"], // emerald
};

/** Darkest stop in each choropleth ramp — used for linked UI/tooltip accents. */
function darkestColor(metric) {
    const ramp = METRIC_COLOR_RAMPS[metric] || METRIC_COLOR_RAMPS.risk_score;
    return ramp[ramp.length - 1];
}

/**
 * Main tooltip line for a panel metric: one decimal for most maps; extra digits for
 * very small risk scores.
 */
function _fmtPanelTooltip(v, metric) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "NA";
    // Rule: show 2 decimals when typical magnitude is < 2.
    // Keep a bit more precision for very small risk values so differences are still readable.
    if (metric === "risk_score") {
        if (Math.abs(n) < 0.01) return n.toFixed(3);
        if (Math.abs(n) < 2) return n.toFixed(2);
        return n.toFixed(1);
    }
    if (Math.abs(n) < 2) return n.toFixed(2);
    return n.toFixed(1);
}

/** Legend axis: one decimal (non-risk); risk uses more decimals when the county range is small. */
function legendTickFormatForMetric(metric, domain) {
    if (metric !== "risk_score") return d3.format(".1f");
    const lo = domain[0];
    const hi = domain[1];
    const span = Number(hi) - Number(lo);
    const m = Math.max(Math.abs(Number(lo)), Math.abs(Number(hi)), span, 1e-9);
    if (m < 0.01) return d3.format(".4f");
    if (m < 0.1) return d3.format(".3f");
    if (m < 0.5) return d3.format(".2f");
    return d3.format(".1f");
}

/**
 * d3's default "nice" ticks often omit the exact data min/max. Always merge endpoints
 * so the legend matches the color ramp (notably the risk map's county window).
 */
function legendTickValues(domain, maxInnerTicks = 4) {
    const lo = domain[0];
    const hi = domain[1];
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
    if (lo === hi) return [lo];
    const inner = d3.ticks(lo, hi, maxInnerTicks);
    const raw = [lo, ...inner, hi].filter((x) => Number.isFinite(x));
    raw.sort((a, b) => a - b);
    const span = Math.max(hi - lo, Number.EPSILON);
    const dedupeEps = Math.max(1e-9, span * 1e-6);
    const out = [raw[0]];
    for (let i = 1; i < raw.length; i++) {
        if (raw[i] - out[out.length - 1] > dedupeEps) {
            out.push(raw[i]);
        }
    }
    return out;
}

function _tooltipRowCols(metric, label, valueInner, qualInner, labelBlack) {
    const c = labelBlack ? "#000" : darkestColor(metric);
    const q = qualInner
        ? `<span class="tooltip-qual">${qualInner}</span>`
        : `<span class="tooltip-qual tooltip-qual--empty"></span>`;
    return (
        `<span class="tooltip-label" style="color:${c}"><b>${label}</b></span>` +
        `<span class="tooltip-value">${valueInner}</span>` +
        q
    );
}

function _escapeHtml(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _splitValueAndQualifier(formatted) {
    const s = String(formatted ?? "");
    const m = s.match(/^(.*?)(?:\s+(\[[^\]]+\]))\s*$/);
    if (!m) return { value: s, qual: "" };
    const value = (m[1] || "").trim();
    const qual = (m[2] || "").trim();
    // If it didn't actually end with a bracketed qualifier, keep whole string as value.
    if (!qual.startsWith("[") || !qual.endsWith("]")) return { value: s, qual: "" };
    return { value, qual };
}


function _computeDomainForMetric(metric, features) {
    // Default: metrics are already normalized to [0,1] in the pipeline.
    if (metric !== "risk_score") return [0, 1];
    // Risk can be very small due to multiplicative formula; for visualization we min-max scale within the selected county.
    const vals = [];
    for (const f of features || []) {
        const v = f && f.properties ? f.properties[metric] : null;
        const n = Number(v);
        if (Number.isFinite(n)) vals.push(n);
    }
    if (!vals.length) return [0, 1];
    let min = Math.min(...vals);
    let max = Math.max(...vals);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
    if (min === max) {
        // Avoid degenerate scale; keep a tiny span.
        const eps = min === 0 ? 1e-6 : Math.abs(min) * 0.01;
        min = Math.max(0, min - eps);
        max = max + eps;
    }
    return [min, max];
}

function colorScaleForMetric(metric, features) {
    const stops = METRIC_COLOR_RAMPS[metric] || METRIC_COLOR_RAMPS.risk_score;
    const domain = _computeDomainForMetric(metric, features);
    return d3.scaleSequential(d3.interpolateRgbBasis(stops)).domain(domain);
}

function _qualityFor(p, key) {
    const raw = p[key + "_source"] || "MISSING";
    if (raw === "DUMMY") return "MISSING";
    return raw;
}

function _abbrToken(s) {
    const t = String(s || "").toLowerCase();
    if (t.includes("acs")) return "acs";
    if (t.includes("census")) return "census";
    if (t.includes("hifld")) return "hifld";
    if (t.includes("osm")) return "osm";
    if (t.includes("whp")) return "whp";
    if (t.includes("nlcd")) return "nlcd";
    if (t.includes("tract")) return "tract";
    if (t.includes("county mean") || t.includes("county-mean") || t.includes("county mean")) return "county-mean";
    if (t.includes("impute")) return "impute";
    return "misc";
}

function _debugTag(p, key) {
    if (key === "eal" || key === "eal_norm") {
        return _debugTagEalFamily(p, key);
    }
    const q = _qualityFor(p, key);
    const prov = p[key + "_provenance"] || "";
    if (q === "REAL") return `[src:${_abbrToken(prov)}]`;
    if (q === "ESTIMATED") return `[est:${_abbrToken(prov)}]`;
    if (q === "PROXY") return `[px:${_abbrToken(prov)}]`;
    return `[missing]`;
}

/** EAL / eal_norm inherit display quality from exposure_building_value (calculations.csv). */
function _qualityForEalFamily(p, key) {
    const bq = _qualityFor(p, "exposure_building_value");
    if (bq === "MISSING") return "MISSING";
    if (bq === "ESTIMATED" || bq === "PROXY") return bq;
    return "REAL";
}

function _debugTagEalFamily(p, key) {
    const bq = _qualityFor(p, "exposure_building_value");
    const prov = p.exposure_building_value_provenance || "";
    if (bq === "MISSING") return `[missing]`;
    if (bq === "REAL") return `[src:${_abbrToken(prov)}]`;
    if (bq === "ESTIMATED") return `[est:${_abbrToken(prov)}]`;
    if (bq === "PROXY") return `[px:${_abbrToken(prov)}]`;
    return `[missing]`;
}

function _formatValue(p, key, fmt) {
    const q = (key === "eal" || key === "eal_norm") ? _qualityForEalFamily(p, key) : _qualityFor(p, key);
    const v = p[key];
    const missing = q === "MISSING" || v == null || (typeof v === "number" && !Number.isFinite(v));
    if (missing) return `— ${_debugTag(p, key)}`.trim();
    // If caller formats to 1 decimal but the value is small (<2), upgrade to 2 decimals
    // for readability (matches panel header rule).
    let base = fmt(v);
    const n = Number(v);
    if (Number.isFinite(n) && Math.abs(n) < 2) {
        const s = String(base);
        if (/^-?\d+(?:\.\d+)?$/.test(s) && /\.\d$/.test(s)) {
            base = n.toFixed(2);
        }
    }
    const star = (q === "ESTIMATED" || q === "PROXY") ? "*" : "";
    const tag = _debugTag(p, key);
    return `${base}${star}${tag ? " " + tag : ""}`;
}

const projection = d3.geoMercator();
const path = d3.geoPath().projection(projection);

/** Shared across all six maps; use identity after each county load. */
let mapZoomTransform = d3.zoomIdentity;
let _mapZoomPropagating = false;

// Zoom policy:
// - We treat the initial fit-to-panel view as the most zoomed-out useful view (k = 1).
// - Users can zoom in to inspect individual polygons (k up to ZOOM_K_MAX).
const ZOOM_K_MIN = 1.0;
const ZOOM_K_MAX = 30.0;
// ~5mm on a typical screen is ~18–20px; use 20px as a visible, consistent margin.
const FIT_MARGIN_PX = 20;
const LEGEND_H_PX = 46;

const mapZoom = d3
    .zoom()
    .scaleExtent([ZOOM_K_MIN, ZOOM_K_MAX])
    .on("zoom", function (event) {
        mapZoomTransform = event.transform;
        d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
        updateZoomSliderFromTransform();

        // Sync all six maps only when the zoom came from a user interaction on one of them.
        // (Programmatic transforms from slider/reset don't have a sourceEvent.)
        if (event.sourceEvent && !_mapZoomPropagating) {
            _mapZoomPropagating = true;
            d3.selectAll("svg.map-svg")
                .filter(function () {
                    return this !== event.currentTarget;
                })
                .call(mapZoom.transform, mapZoomTransform);
            _mapZoomPropagating = false;
        }
    });

let _mapZoomInstalled = false;

// --- Zoom slider (shared, flush right) ---
const zoomKToSlider = d3.scaleLog().domain([ZOOM_K_MIN, ZOOM_K_MAX]).range([0, 100]).clamp(true);
const sliderToZoomK = d3.scaleLog().domain([1, 100]).range([ZOOM_K_MIN, ZOOM_K_MAX]).clamp(true);
let _zoomSliderSyncing = false;

function updateZoomSliderFromTransform() {
    if (_zoomSliderSyncing) return;
    const k = mapZoomTransform && Number.isFinite(mapZoomTransform.k) ? mapZoomTransform.k : 1;
    const v = zoomKToSlider(k);
    _zoomSliderSyncing = true;
    document.querySelectorAll("input.zoom-slider").forEach((el) => {
        el.value = String(Math.round(v));
    });
    _zoomSliderSyncing = false;
}

function setZoomKFromSliderValue(rawValue) {
    const v = Number(rawValue);
    if (!Number.isFinite(v)) return;
    const safe = Math.min(100, Math.max(1, v)); // avoid log(0)
    const newK = sliderToZoomK(safe);
    // Scale about the visual center of each map.
    const { width: w, height: h } = getCellDimensions();
    const cx = w / 2;
    const cy = h / 2;
    // Apply to one map; zoom handler updates global transform.
    const first = d3.select("svg.map-svg");
    if (first.empty()) return;
    first.call(mapZoom.scaleTo, newK, [cx, cy]);
    // Now propagate to all maps (programmatic, so the handler won't auto-propagate).
    _mapZoomPropagating = true;
    d3.selectAll("svg.map-svg")
        .filter(function () {
            return this !== first.node();
        })
        .call(mapZoom.transform, mapZoomTransform);
    _mapZoomPropagating = false;
}

function resetMapView() {
    mapZoomTransform = d3.zoomIdentity;
    d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
    updateZoomSliderFromTransform();
    _mapZoomPropagating = true;
    d3.selectAll("svg.map-svg").call(mapZoom.transform, mapZoomTransform);
    _mapZoomPropagating = false;
}

let geoData;
let countyManifest;
let _mergedAllUiDoc = null;

const tooltip = d3.select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

function buildTooltip(p) {
    const rowFromFormatted = (metric, label, formatted, labelBlack) => {
        const parts = _splitValueAndQualifier(formatted);
        return _tooltipRowCols(metric, label, parts.value, parts.qual, labelBlack);
    };

    const scoresHtml = [
        _tooltipRowCols("risk_score", "Risk:", _fmtPanelTooltip(p.risk_score, "risk_score"), "", false),
        _tooltipRowCols("hazard_score", "Hazard:", _fmtPanelTooltip(p.hazard_score, "hazard_score"), "", false),
        _tooltipRowCols("exposure_score", "Exposure:", _fmtPanelTooltip(p.exposure_score, "exposure_score"), "", false),
        _tooltipRowCols("vulnerability_score", "Vulnerability:", _fmtPanelTooltip(p.vulnerability_score, "vulnerability_score"), "", false),
        _tooltipRowCols("resilience_score", "Resilience:", _fmtPanelTooltip(p.resilience_score, "resilience_score"), "", false),
        _tooltipRowCols("eal_norm", "EAL (norm):", _fmtPanelTooltip(p.eal_norm, "eal_norm"), "", false),
    ].join("");

    const bigHtml = [
        rowFromFormatted("exposure_score", "Population:", _formatValue(p, "exposure_population", v => Number(v).toLocaleString()), true),
        rowFromFormatted("exposure_score", "Housing units:", _formatValue(p, "exposure_housing", v => Math.round(v).toLocaleString()), true),
        rowFromFormatted("exposure_score", "Building value:", _formatValue(p, "exposure_building_value", v => "$" + Math.round(v).toLocaleString()), true),
        rowFromFormatted("eal_norm", "Expected loss (USD):", _formatValue(p, "eal", v => "$" + Math.round(v).toLocaleString()), false),
    ].join("");

    const parts = [scoresHtml, `<hr class="tooltip-hr"/>`, bigHtml];

    let diag = p.diagnostics;
    if (typeof diag === "string") {
        try { diag = JSON.parse(diag); } catch (e) { diag = {}; }
    }
    let diagText = "No validation issues.";
    if (diag && typeof diag === "object" && Object.keys(diag).length > 0) {
        diagText = Object.entries(diag)
            .map(([field, issues]) => {
                const arr = Array.isArray(issues) ? issues : [issues];
                return `${field}: ${arr.join("; ")}`;
            })
            .join("; ");
    }

    const hazardDebug = [
        rowFromFormatted("hazard_score", "hazard_wildfire:", _formatValue(p, "hazard_wildfire", v => Number(v).toFixed(1)), false),
        rowFromFormatted("hazard_score", "hazard_vegetation:", _formatValue(p, "hazard_vegetation", v => Number(v).toFixed(1)), false),
        rowFromFormatted("hazard_score", "hazard_forest_distance:", _formatValue(p, "hazard_forest_distance", v => Number(v).toFixed(1)), false),
    ].join("");

    const vulnDebug = [
        rowFromFormatted("vulnerability_score", "vuln_poverty:", _formatValue(p, "vuln_poverty", v => Number(v).toFixed(1)), false),
        rowFromFormatted("vulnerability_score", "vuln_elderly:", _formatValue(p, "vuln_elderly", v => Number(v).toFixed(1)), false),
        rowFromFormatted("vulnerability_score", "vuln_uninsured:", _formatValue(p, "vuln_uninsured", v => Number(v).toFixed(1)), false),
    ].join("");

    const resDebug = [
        rowFromFormatted("resilience_score", "res_vehicle_access:", _formatValue(p, "res_vehicle_access", v => Number(v).toFixed(1)), false),
        rowFromFormatted("resilience_score", "res_median_household_income:", _formatValue(p, "res_median_household_income", v => Number(v).toFixed(0)), false),
        rowFromFormatted("resilience_score", "res_internet_access:", _formatValue(p, "res_internet_access", v => Number(v).toFixed(1)), false),
    ].join("");

    parts.push(
        `<hr class="tooltip-hr"/>`,
        `<div class="tooltip-diag"><b>Diagnostics:</b> ${_escapeHtml(diagText)}</div>`,
        `<hr class="tooltip-hr"/>`,
        `<div class="tooltip-section-title">Hazard inputs</div>`,
        hazardDebug,
        `<div class="tooltip-section-title">Vulnerability inputs</div>`,
        vulnDebug,
        `<div class="tooltip-section-title">Resilience inputs</div>`,
        resDebug
    );

    return `<div class="tooltip-body">${parts.join("")}</div>`;
}

function attachTooltipHandlers(selection) {
    selection
        .on("mouseover", function (event, d) {
            const p = d.properties;
            const bid = blockKeyFromProperties(p);
            hoveredBlockId = bid || null;
            updateBlockHighlight();
            tooltip.transition().duration(200).style("opacity", .9);
            tooltip.html(buildTooltip(p))
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mousemove", function (event) {
            tooltip
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", function (event, d) {
            const bid = blockKeyFromProperties(d.properties);
            const rt = event.relatedTarget;
            if (rt && typeof rt.closest === "function") {
                const nextPath = rt.closest("path.block-feature");
                if (nextPath && (nextPath.getAttribute("data-block-id") || "") === bid) {
                    return;
                }
            }
            hoveredBlockId = null;
            updateBlockHighlight();
            tooltip.transition().duration(200).style("opacity", 0);
        });
}

function fitProjectionToGeo(mapWidth, mapHeight) {
    const effH = Math.max(20, mapHeight - LEGEND_H_PX);
    const extent = [
        [FIT_MARGIN_PX, FIT_MARGIN_PX],
        [Math.max(FIT_MARGIN_PX + 1, mapWidth - FIT_MARGIN_PX), Math.max(FIT_MARGIN_PX + 1, effH - FIT_MARGIN_PX)],
    ];
    if (geoData && geoData.features && geoData.features.length > 0) {
        projection.fitExtent(extent, geoData);
    } else {
        projection
            .scale(1)
            .translate([mapWidth / 2, mapHeight / 2]);
        const outline = { type: "Feature", geometry: { type: "Polygon", coordinates: [[[-125, 24], [-66, 24], [-66, 50], [-125, 50], [-125, 24]]] } };
        projection.fitExtent(extent, outline);
    }
}

function getCellDimensions() {
    const first = document.querySelector("#map-panel-eal svg.map-svg");
    if (first) {
        // Prefer the rendered box (CSS-scaled), not the static attributes.
        const r = first.getBoundingClientRect();
        const w = Number.isFinite(r.width) && r.width > 0 ? r.width : (+first.getAttribute("width") || 320);
        const h = Number.isFinite(r.height) && r.height > 0 ? r.height : (+first.getAttribute("height") || 220);
        return { width: w, height: h };
    }
    return { width: 320, height: 220 };
}

function renderAll() {
    const { width: mapW, height: mapH } = getCellDimensions();
    fitProjectionToGeo(mapW, mapH);
    hoveredBlockId = null;
    const features = (geoData && geoData.features) ? geoData.features : [];

    for (const { panelId, metric } of MAP_PANELS) {
        const mapSvg = d3.select(`#${panelId} svg.map-svg`);
        const legendSvg = d3.select(`#${panelId} svg.legend-svg`);
        if (mapSvg.empty()) continue;

        const domain = _computeDomainForMetric(metric, features);
        const color = colorScaleForMetric(metric, features);
        const gradientId = `legend-gradient-${metric}`;

        mapSvg.selectAll("*").remove();
        if (!legendSvg.empty()) legendSvg.selectAll("*").remove();

        const zoomLayer = mapSvg.append("g").attr("class", "map-zoom-layer");
        zoomLayer
            .selectAll("path")
            .data(features)
            .join("path")
            .attr("class", "block-feature")
            .attr("data-block-id", d => blockKeyFromProperties(d.properties))
            .attr("d", path)
            .attr("fill", d => {
                const v = d.properties[metric];
                return v != null && !isNaN(v) ? color(v) : "#ccc";
            })
            .attr("stroke", "#333")
            .attr("stroke-width", BASE_STROKE)
            .call(attachTooltipHandlers);

        if (legendSvg.empty()) continue;

        // Extra side margin so min/max tick labels don't touch the SVG edge.
        const sideMargin = 14;
        const legendNode = legendSvg.node();
        const rr = legendNode && legendNode.getBoundingClientRect ? legendNode.getBoundingClientRect() : null;
        const svgW = rr && Number.isFinite(rr.width) && rr.width > 0 ? rr.width : (+legendSvg.attr("width") || 440);
        const legendWidth = Math.max(140, svgW - sideMargin * 2);
        const legendBarH = 12;
        const gx = sideMargin;
        const accent = darkestColor(metric);

        const defs = legendSvg.append("defs");
        const gradient = defs.append("linearGradient")
            .attr("id", gradientId);

        gradient.selectAll("stop")
            .data(d3.range(0, 1.01, 0.05))
            .enter()
            .append("stop")
            .attr("offset", d => d * 100 + "%")
            .attr("stop-color", d => color(domain[0] + d * (domain[1] - domain[0])));

        const legendGroup = legendSvg.append("g")
            .attr("transform", `translate(${gx}, 8)`);

        legendGroup.append("rect")
            .attr("width", legendWidth)
            .attr("height", legendBarH)
            .style("fill", `url(#${gradientId})`);

        const scale = d3.scaleLinear()
            .domain(domain)
            .range([0, legendWidth]);

        const tickFmt = legendTickFormatForMetric(metric, domain);

        const axis = d3.axisBottom(scale)
            .tickValues(legendTickValues(domain, 4))
            .tickFormat(tickFmt)
            .tickPadding(6);

        const axisG = legendGroup.append("g")
            .attr("transform", `translate(0,${legendBarH})`);
        axisG.call(axis);
        axisG.selectAll("text")
            .attr("font-size", "10px")
            .attr("fill", accent);
        axisG.selectAll("line")
            .attr("stroke", accent);
        axisG.select(".domain")
            .attr("stroke", accent);
    }

    d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
    if (!_mapZoomInstalled) {
        d3.selectAll("svg.map-svg")
            .call(mapZoom)
            .on("dblclick.zoom", (event) => {
                event.preventDefault();
                resetMapView();
            });
        _mapZoomInstalled = true;
    }
    d3.selectAll("svg.map-svg").call(mapZoom.transform, mapZoomTransform);
    updateZoomSliderFromTransform();

    updateBlockHighlight();
}

function applyMapDetailMode(on) {
    const viz = document.getElementById("mapViz");
    const legend = document.getElementById("mapDetailLegend");
    if (viz) viz.classList.toggle("map-viz--detail", !!on);
    if (legend) legend.hidden = !on;
    renderAll();
}

function _safeNumber(x, fallback = null) {
    const v = Number(x);
    return Number.isFinite(v) ? v : fallback;
}

function _firstScalar(features, prop, fallback = null) {
    if (!features || !features.length) return fallback;
    const p = features[0] && features[0].properties ? features[0].properties : {};
    if (!p) return fallback;
    return p[prop] != null ? p[prop] : fallback;
}

function _parseJsonMaybe(value) {
    if (value == null) return null;
    if (typeof value === "object") return value;
    if (typeof value !== "string") return null;
    try { return JSON.parse(value); } catch (e) { return null; }
}

function _pillClassForSource(source) {
    const s = String(source || "").toUpperCase();
    if (s === "REAL") return "validation-pill--real";
    if (s === "PROXY") return "validation-pill--proxy";
    if (s === "DUMMY") return "validation-pill--dummy";
    return "validation-pill--unknown";
}

function _pillClassForBurnedSource(source) {
    const s = String(source || "").toUpperCase();
    if (s === "MTBS") return "validation-pill--mtbs";
    if (s === "PROXY") return "validation-pill--burned-proxy";
    return "validation-pill--unknown";
}

function _formatMetricValue(v) {
    if (v == null || v === "") return "—";
    const n = Number(v);
    if (!Number.isFinite(n)) return "—";
    if (n !== 0 && (Math.abs(n) >= 1e5 || Math.abs(n) < 1e-4)) {
        return n.toExponential(3);
    }
    return n.toFixed(3);
}

function _countBurnedLabels(features) {
    let pos = 0;
    let neg = 0;
    let unk = 0;
    for (const f of features) {
        const p = f && f.properties;
        if (!p) {
            unk++;
            continue;
        }
        const v = p._burned_label;
        if (v == null) {
            unk++;
            continue;
        }
        const n = Number(v);
        if (n === 1) pos++;
        else if (n === 0) neg++;
        else unk++;
    }
    return { pos, neg, unk, total: features.length };
}

function buildValidationMetricsFromFeatures(features) {
    const p0 = (features[0] && features[0].properties) || {};
    const fema = _parseJsonMaybe(p0.fema_nri_comparison) || {};
    const moduleSensitivity = _parseJsonMaybe(p0.module_sensitivity) || {};
    const calfireValidation = _parseJsonMaybe(p0.calfire_validation) || {};
    const burned = _countBurnedLabels(features);
    return {
        block_rows: features.length,
        fire_overlap_ratio: _safeNumber(p0.fire_overlap_ratio, null),
        auc_score: _safeNumber(p0.auc_score, null),
        risk_concentration: _safeNumber(p0.risk_concentration, null),
        gini_risk: _safeNumber(p0.gini_risk, null),
        fema_nri_comparison: fema,
        module_sensitivity: moduleSensitivity,
        calfire_validation: calfireValidation,
        county_risk: _safeNumber(p0.county_risk, null),
        county_eal: p0.county_eal != null && p0.county_eal !== "" ? Number(p0.county_eal) : null,
        block_to_county_mapping: p0.block_to_county_mapping,
        external_sources: {
            fema_nri: String(fema.source != null ? fema.source : "UNKNOWN"),
            burned_labels: String(p0._burned_label_source != null ? p0._burned_label_source : "UNKNOWN"),
            burned_pos: burned.pos,
            burned_neg: burned.neg
        }
    };
}

function validationMetricsToChartData(m) {
    const fema = m.fema_nri_comparison || {};
    const cal = m.calfire_validation || {};
    const out = [
        { key: "fire_overlap_ratio", label: "Overlap", value: _safeNumber(m.fire_overlap_ratio, null), domain: [0, 1], color: "#E65100" },
        { key: "auc_score", label: "AUC", value: _safeNumber(m.auc_score, null), domain: [0, 1], color: "#B71C1C" },
        { key: "risk_concentration", label: "Top 10%", value: _safeNumber(m.risk_concentration, null), domain: [0, 1], color: "#0369A1" },
        { key: "gini_risk", label: "Gini", value: _safeNumber(m.gini_risk, null), domain: [0, 1], color: "#5B21B6" }
    ];
    const caAuc = _safeNumber(
        (cal && cal.overall && cal.overall.top_pct_metrics) ? cal.overall.top_pct_metrics.auc : cal.auc,
        null
    );
    if (caAuc != null) {
        out.push({ key: "calfire_auc", label: "CAL FIRE AUC", value: caAuc, domain: [0, 1], color: "#7C2D12" });
    }
    const cr = _safeNumber(fema.corr_risk, null);
    out.push({ key: "fema_corr_risk", label: "FEMA ρ (risk)", value: cr, domain: [-1, 1], color: "#166534" });
    const ce = _safeNumber(fema.corr_eal, null);
    if (ce != null) {
        out.push({ key: "fema_corr_eal", label: "FEMA ρ (EAL)", value: ce, domain: [-1, 1], color: "#15803d" });
    }
    return out;
}

function kpiHtmlFromMetrics(m, opts) {
    const options = opts || {};
    const joint = !!options.joint;
    const fema = m.fema_nri_comparison || {};
    const ext = m.external_sources || {};
    const femaSource = String(fema.source != null ? fema.source : ext.fema_nri || "UNKNOWN");
    const burnSrc = String(ext.burned_labels != null ? ext.burned_labels : "UNKNOWN");
    const fail = options.threshold_failures || {};
    const failKeys = fail && typeof fail === "object" ? Object.keys(fail) : [];

    const parts = [];

    if (joint) {
        const ok = options.passed;
        const passClass = ok ? "validation-pill--pass" : "validation-pill--fail";
        const passText = ok ? "thresholds OK" : "thresholds fail";
        parts.push(
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Run status</span>
                <span class="validation-pill ${passClass}">${_escapeHtml(passText)}</span>
                <span class="validation-kpi__meta">validation_thresholds.json</span>
            </div>`
        );
        if (options.county_fips && options.county_fips.length) {
            parts.push(
                `<div class="validation-kpi">
                    <span class="validation-kpi__label">Counties in join</span>
                    <span class="validation-kpi__value">${_escapeHtml(options.county_fips.join(", "))}</span>
                    <span class="validation-kpi__meta">county_fips</span>
                </div>`
            );
        }
    }

    parts.push(
        `<div class="validation-kpi">
            <span class="validation-kpi__label">Block rows</span>
            <span class="validation-kpi__value">${m.block_rows != null ? String(m.block_rows) : "—"}</span>
            <span class="validation-kpi__meta">block_rows</span>
        </div>`
    );

    if (m.county_risk != null && Number.isFinite(Number(m.county_risk))) {
        parts.push(
            `<div class="validation-kpi">
                <span class="validation-kpi__label">County mean risk</span>
                <span class="validation-kpi__value">${Number(m.county_risk).toFixed(3)}</span>
                <span class="validation-kpi__meta">county_risk (aggregated)</span>
            </div>`
        );
    }
    if (m.county_eal != null && Number.isFinite(Number(m.county_eal))) {
        parts.push(
            `<div class="validation-kpi">
                <span class="validation-kpi__label">County EAL (sum)</span>
                <span class="validation-kpi__value">${_formatMetricValue(m.county_eal)}</span>
                <span class="validation-kpi__meta">county_eal</span>
            </div>`
        );
    }
    if (m.block_to_county_mapping != null && m.block_to_county_mapping !== "") {
        parts.push(
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Block FIPS (sample)</span>
                <span class="validation-kpi__value">${_escapeHtml(String(m.block_to_county_mapping))}</span>
                <span class="validation-kpi__meta">block_to_county_mapping</span>
            </div>`
        );
    }

    parts.push(
        `<div class="validation-kpi">
            <span class="validation-kpi__label">MTBS overlap</span>
            <span class="validation-kpi__value">${_formatMetricValue(m.fire_overlap_ratio)}</span>
            <span class="validation-kpi__meta">fire_overlap_ratio</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">AUC</span>
            <span class="validation-kpi__value">${_formatMetricValue(m.auc_score)}</span>
            <span class="validation-kpi__meta">auc_score</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">Concentration (top 10%)</span>
            <span class="validation-kpi__value">${_formatMetricValue(m.risk_concentration)}</span>
            <span class="validation-kpi__meta">risk_concentration</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">Gini (risk)</span>
            <span class="validation-kpi__value">${_formatMetricValue(m.gini_risk)}</span>
            <span class="validation-kpi__meta">gini_risk</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">Burned labels</span>
            <span class="validation-kpi__value">pos ${ext.burned_pos != null ? ext.burned_pos : "—"} / neg ${ext.burned_neg != null ? ext.burned_neg : "—"}</span>
            <span class="validation-kpi__meta">_burned_label</span>
            <span class="validation-pill ${_pillClassForBurnedSource(burnSrc)}">${_escapeHtml(burnSrc)}</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">FEMA n_counties</span>
            <span class="validation-kpi__value">${fema.n_counties != null ? String(fema.n_counties) : "—"}</span>
            <span class="validation-kpi__meta">join width for corr</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">FEMA corr (risk)</span>
            <span class="validation-kpi__value">${_formatMetricValue(fema.corr_risk)}</span>
            <span class="validation-kpi__meta">corr_risk</span>
            <span class="validation-pill ${_pillClassForSource(femaSource)}">${_escapeHtml(femaSource)}</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">FEMA RMSE (risk)</span>
            <span class="validation-kpi__value">${_formatMetricValue(fema.rmse_risk)}</span>
            <span class="validation-kpi__meta">rmse_risk</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">FEMA corr (EAL)</span>
            <span class="validation-kpi__value">${_formatMetricValue(fema.corr_eal)}</span>
            <span class="validation-kpi__meta">corr_eal</span>
        </div>`,
        `<div class="validation-kpi">
            <span class="validation-kpi__label">FEMA RMSE (EAL)</span>
            <span class="validation-kpi__value">${_formatMetricValue(fema.rmse_eal)}</span>
            <span class="validation-kpi__meta">rmse_eal</span>
        </div>`
    );

    // Experiment 1: module sensitivity (Pearson r + p-value).
    const ms = m.module_sensitivity || {};
    const mods = (ms && ms.modules) ? ms.modules : {};
    if (mods && (mods.hazard || mods.exposure || mods.vulnerability || mods.resilience)) {
        const fmtRp = (obj) => {
            if (!obj) return "—";
            const r = obj.r;
            const p = obj.p;
            const rs = (r == null || !Number.isFinite(Number(r))) ? "—" : Number(r).toFixed(3);
            const ps = (p == null || !Number.isFinite(Number(p))) ? "—" : Number(p).toExponential(2);
            return `r ${rs}, p ${ps}`;
        };
        const scope = ms.scope ? String(ms.scope) : "all_rows_in_frame";
        parts.push(
            `<div class="validation-kpi" style="min-width:min(100%, 520px)">
                <span class="validation-kpi__label">Experiment 1 (Pearson)</span>
                <span class="validation-kpi__meta">${_escapeHtml(scope)}: corr(module, risk_score)</span>
            </div>`,
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Hazard → Risk</span>
                <span class="validation-kpi__value">${_escapeHtml(fmtRp(mods.hazard))}</span>
                <span class="validation-kpi__meta">hazard_score vs risk_score</span>
            </div>`,
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Exposure → Risk</span>
                <span class="validation-kpi__value">${_escapeHtml(fmtRp(mods.exposure))}</span>
                <span class="validation-kpi__meta">exposure_score vs risk_score</span>
            </div>`,
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Vulnerability → Risk</span>
                <span class="validation-kpi__value">${_escapeHtml(fmtRp(mods.vulnerability))}</span>
                <span class="validation-kpi__meta">vulnerability_score vs risk_score</span>
            </div>`,
            `<div class="validation-kpi">
                <span class="validation-kpi__label">Resilience → Risk</span>
                <span class="validation-kpi__value">${_escapeHtml(fmtRp(mods.resilience))}</span>
                <span class="validation-kpi__meta">resilience_score vs risk_score</span>
            </div>`
        );
    }

    // Experiment 2 – Historical Fire Validation (CAL FIRE; show both threshold modes + per-county when available).
    const calRoot = m.calfire_validation || {};
    const calSrc = calRoot.source != null ? String(calRoot.source) : "";
    const calOverall = calRoot.overall || null;
    const calByCounty = calRoot.by_county || null;
    const currentFips = (options && options.current_county_fips) ? String(options.current_county_fips) : "";
    const cal = joint ? calOverall : (calByCounty && currentFips ? calByCounty[currentFips] : null);

    const minPos = 30;
    const topPctMetrics = cal && cal.top_pct_metrics ? cal.top_pct_metrics : null;
    const topKMetrics = cal && cal.top_k_metrics ? cal.top_k_metrics : null;
    const burnedTotal = topPctMetrics ? topPctMetrics.burned_total : null;

    if (calRoot && (topPctMetrics || topKMetrics)) {
        const y0 = calRoot.year_min != null ? String(calRoot.year_min) : "—";
        const y1 = calRoot.year_max != null ? String(calRoot.year_max) : "—";
        const topPct = (Number(cal && cal.top_pct != null ? cal.top_pct : 0.1) * 100);
        const topPctText = Number.isFinite(topPct) ? `${topPct.toFixed(0)}%` : "—";
        const topK = cal && cal.top_k != null ? String(cal.top_k) : "—";

        const insufficient = burnedTotal != null && Number(burnedTotal) < minPos;
        const scopeLabel = joint ? "all packaged counties" : (currentFips ? `county ${currentFips}` : "current county");

        const rowBlock = (label, metrics, predLabel) => {
            if (!metrics) return "";
            const burnedText = `${metrics.burned_total != null ? String(metrics.burned_total) : "—"} of ${metrics.n_total != null ? String(metrics.n_total) : "—"}`;
            const predText = `${metrics.predicted_high_risk != null ? String(metrics.predicted_high_risk) : "—"}`;
            const tpfpText = `${metrics.tp != null ? String(metrics.tp) : "—"} / ${metrics.fp != null ? String(metrics.fp) : "—"}`;
            const prfText = `${_formatMetricValue(metrics.precision)} / ${_formatMetricValue(metrics.recall)} / ${_formatMetricValue(metrics.f1)}`;
            return (
                `<tr class="validation-table__section"><td colspan="3"><b>${_escapeHtml(label)}</b> <span class="validation-kpi__meta">${_escapeHtml(predLabel)}</span></td></tr>` +
                `<tr><td>Block groups that burned (ground truth)</td><td>${_escapeHtml(burnedText)}</td><td>CAL FIRE FRAP perimeters</td></tr>` +
                `<tr><td>Predicted high-risk</td><td>${_escapeHtml(predText)}</td><td>Model <code>risk_score</code></td></tr>` +
                `<tr><td>True Positives / False Positives</td><td>${_escapeHtml(tpfpText)}</td><td>CAL FIRE + <code>risk_score</code></td></tr>` +
                `<tr><td>Precision / Recall / F1</td><td>${_escapeHtml(prfText)}</td><td>CAL FIRE + <code>risk_score</code></td></tr>` +
                `<tr><td>Accuracy</td><td>${_escapeHtml(_formatMetricValue(metrics.accuracy))}</td><td>CAL FIRE + <code>risk_score</code></td></tr>` +
                `<tr><td>AUC</td><td>${_escapeHtml(_formatMetricValue(metrics.auc))}</td><td>CAL FIRE + <code>risk_score</code></td></tr>`
            );
        };

        parts.push(
            `<div class="validation-kpi validation-kpi--table">
                <div class="validation-kpi__table-head">
                    <span class="validation-kpi__label">Experiment 2 – Historical Fire Validation</span>
                    <span class="validation-kpi__meta">${_escapeHtml(y0)}–${_escapeHtml(y1)} (${_escapeHtml(scopeLabel)})</span>
                    <span class="validation-pill ${_pillClassForSource(calSrc)}">${_escapeHtml(calSrc || "UNKNOWN")}</span>
                </div>
                ${
                    insufficient
                        ? `<div class="validation-kpi__meta">Insufficient burned positives for stable per-county KPIs (need ≥ ${minPos}).</div>`
                        : ""
                }
                <table class="validation-table" role="table" aria-label="Experiment 2 – Historical Fire Validation">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Data source</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowBlock(`Mode A`, topPctMetrics, `predicted = top ${topPctText}`)}
                        ${rowBlock(`Mode B`, topKMetrics, `predicted = top K (K = burned_total = ${topK})`)}
                    </tbody>
                </table>
            </div>`
        );
    }

    if (joint && failKeys.length) {
        const brief = failKeys.map((k) => `${k}`).join(", ");
        parts.push(
            `<div class="validation-kpi" style="min-width:min(100%, 520px)">
                <span class="validation-kpi__label">Threshold failures</span>
                <span class="validation-kpi__meta">${_escapeHtml(brief)}</span>
            </div>`
        );
    }

    return parts.join("");
}

function renderValidationBarChart(chart, data, heightPx) {
    if (!data || !data.length) {
        chart.selectAll("*").remove();
        return;
    }
    const hTotal = heightPx != null ? heightPx : 200;
    const svgNode = chart.node();
    const w = (svgNode && svgNode.getBoundingClientRect && svgNode.getBoundingClientRect().width) ? svgNode.getBoundingClientRect().width : (+chart.attr("width") || 900);
    chart.attr("height", hTotal);
    chart.attr("viewBox", `0 0 ${Math.max(320, w)} ${hTotal}`);
    chart.selectAll("*").remove();

    const pad = { l: 14, r: 14, t: 12, b: 12 };
    const innerW = Math.max(200, w - pad.l - pad.r);
    const innerH = Math.max(60, hTotal - pad.t - pad.b);
    const g = chart.append("g").attr("transform", `translate(${pad.l},${pad.t})`);

    const rowH = innerH / data.length;
    const barH = Math.max(8, rowH * 0.5);
    const labelW = Math.min(120, innerW * 0.22);
    const barW = innerW - labelW - 10;

    const rows = g.selectAll("g.row").data(data).join("g").attr("class", "row").attr("transform", (_, i) => `translate(0,${i * rowH})`);

    rows.append("text")
        .attr("x", 0)
        .attr("y", rowH * 0.62)
        .attr("font-size", 11)
        .attr("fill", "#111827")
        .text((d) => d.label);

    rows.append("rect")
        .attr("x", labelW)
        .attr("y", (rowH - barH) / 2)
        .attr("width", barW)
        .attr("height", barH)
        .attr("rx", 6)
        .attr("fill", "#f3f4f6")
        .attr("stroke", "#e5e7eb");

    rows.append("rect")
        .attr("x", (d) => {
            if (d.domain[0] < 0) {
                const x0 = labelW + barW * (0 - d.domain[0]) / (d.domain[1] - d.domain[0]);
                const v = d.value;
                if (v == null) return x0;
                const xv = labelW + barW * (v - d.domain[0]) / (d.domain[1] - d.domain[0]);
                return Math.min(x0, xv);
            }
            return labelW;
        })
        .attr("y", (rowH - barH) / 2)
        .attr("width", (d) => {
            if (d.value == null) return 0;
            if (d.domain[0] < 0) {
                const x0 = barW * (0 - d.domain[0]) / (d.domain[1] - d.domain[0]);
                const xv = barW * (d.value - d.domain[0]) / (d.domain[1] - d.domain[0]);
                return Math.max(0, Math.abs(xv - x0));
            }
            return Math.max(0, Math.min(barW, barW * (d.value - d.domain[0]) / (d.domain[1] - d.domain[0])));
        })
        .attr("height", barH)
        .attr("rx", 6)
        .attr("fill", (d) => d.color)
        .attr("opacity", (d) => (d.value == null ? 0.2 : 0.85));

    rows
        .filter((d) => d.domain[0] < 0)
        .append("line")
        .attr("x1", (d) => {
            const dom = d.domain;
            return labelW + barW * (0 - dom[0]) / (dom[1] - dom[0]);
        })
        .attr("x2", (d) => {
            const dom = d.domain;
            return labelW + barW * (0 - dom[0]) / (dom[1] - dom[0]);
        })
        .attr("y1", (rowH - barH) / 2 - 2)
        .attr("y2", (rowH + barH) / 2 + 2)
        .attr("stroke", "#9ca3af")
        .attr("stroke-width", 1);

    rows.append("text")
        .attr("x", labelW + barW + 6)
        .attr("y", rowH * 0.62)
        .attr("font-size", 11)
        .attr("fill", "#374151")
        .text((d) => (d.value == null ? "—" : Number(d.value).toFixed(3)));
}

function _fmtMoneyShort(n) {
    const v = Number(n);
    if (!Number.isFinite(v)) return "—";
    const abs = Math.abs(v);
    if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
    return `$${Math.round(v).toLocaleString()}`;
}

function renderExperimentsDashboard() {
    const host = document.getElementById("experimentsDashboard");
    if (!host) return;
    if (!_mergedAllUiDoc || !_mergedAllUiDoc.metrics || !_mergedAllUiDoc.metrics.experiments) {
        host.innerHTML = `<div class="exp-card"><div class="exp-card__title">Dashboard</div><div class="exp-card__meta">Missing <code>data/validation/merged_all_counties.json</code>. Re-run: <code>python -m src.validation.run_all --no-write --export-ui data/validation/merged_all_counties.json</code></div></div>`;
        return;
    }

    const exp = _mergedAllUiDoc.metrics.experiments || {};
    const exp1 = exp.experiment1_fema_nri || {};
    const exp2 = Array.isArray(exp.experiment2_county_eal_top10) ? exp.experiment2_county_eal_top10 : [];

    const femaUw = exp1.pearson_unweighted || {};
    const femaPw = exp1.pearson_pop_weighted || {};
    const rUw = femaUw.r != null ? Number(femaUw.r).toFixed(3) : "—";
    const pUw = femaUw.p != null ? Number(femaUw.p).toExponential(2) : (femaUw.n != null && Number(femaUw.n) < 4 ? "n<4" : "—");
    const rPw = femaPw.r != null ? Number(femaPw.r).toFixed(3) : "—";
    const pPw = femaPw.p != null ? Number(femaPw.p).toExponential(2) : (femaPw.n != null && Number(femaPw.n) < 4 ? "n<4" : "—");

    const overlap = exp.experiment3_fire_overlap_ratio != null ? Number(exp.experiment3_fire_overlap_ratio).toFixed(3) : "—";
    const auc = exp.experiment4_auc_score != null ? Number(exp.experiment4_auc_score).toFixed(3) : "—";
    const conc = exp.experiment5_concentration != null ? Number(exp.experiment5_concentration).toFixed(3) : "—";
    const gini = exp.experiment5_gini != null ? Number(exp.experiment5_gini).toFixed(3) : "—";

    const countiesCompared = exp1.counties_compared != null ? String(exp1.counties_compared) : "—";
    const blocks = _mergedAllUiDoc.metrics.block_rows != null ? String(_mergedAllUiDoc.metrics.block_rows) : "—";

    const cards = `
        <div class="exp-cards">
            <div class="exp-card">
                <div class="exp-card__title">Coverage</div>
                <div class="exp-card__value">${_escapeHtml(countiesCompared)}</div>
                <div class="exp-card__meta">counties in FEMA join; blocks in bundle: <b>${_escapeHtml(blocks)}</b></div>
            </div>
            <div class="exp-card">
                <div class="exp-card__title">Exp1 – FEMA NRI</div>
                <div class="exp-card__value">r ${_escapeHtml(rUw)}</div>
                <div class="exp-card__meta">unweighted p ${_escapeHtml(pUw)}; pop‑weighted r ${_escapeHtml(rPw)} (p ${_escapeHtml(pPw)})</div>
            </div>
            <div class="exp-card">
                <div class="exp-card__title">Exp3/4 – Fire history</div>
                <div class="exp-card__value">AUC ${_escapeHtml(auc)}</div>
                <div class="exp-card__meta">overlap@top10: <b>${_escapeHtml(overlap)}</b> (labels: ${_escapeHtml(String(exp.fire_labels_source || "UNKNOWN"))})</div>
            </div>
            <div class="exp-card">
                <div class="exp-card__title">Exp5 – Concentration</div>
                <div class="exp-card__value">${_escapeHtml(conc)}</div>
                <div class="exp-card__meta">top10 share; gini ${_escapeHtml(gini)}</div>
            </div>
        </div>
    `;

    const ealRows = exp2.slice(0, 10).map((r, i) => {
        const fips = r.county_fips != null ? String(r.county_fips) : "—";
        const name = r.county_name != null ? String(r.county_name) : "";
        const eal = _fmtMoneyShort(r.sum_eal);
        const meanRisk = r.mean_risk != null ? Number(r.mean_risk).toFixed(4) : "—";
        return `<tr><td>${i + 1}</td><td>${_escapeHtml(fips)}</td><td>${_escapeHtml(name)}</td><td>${_escapeHtml(eal)}</td><td>${_escapeHtml(meanRisk)}</td></tr>`;
    }).join("");

    const het = Array.isArray(exp.experiment5_heterogeneity_by_county) ? exp.experiment5_heterogeneity_by_county : [];
    const selected = ["06073", "06037", "06059"];
    const selRows = selected.map((fips) => het.find((r) => String(r.county_fips || "") === fips)).filter(Boolean);
    const hetRows = (selRows.length ? selRows : het.slice(0, 10)).map((r) => {
        const fips = r.county_fips != null ? String(r.county_fips) : "—";
        const name = r.county_name != null ? String(r.county_name) : "";
        const mean = r.mean_risk != null ? Number(r.mean_risk).toFixed(4) : "—";
        const mx = r.max_risk != null ? Number(r.max_risk).toFixed(4) : "—";
        const ratio = r.max_mean_ratio != null ? Number(r.max_mean_ratio).toFixed(1) + "×" : "—";
        const top10 = r.top10_share != null ? (Number(r.top10_share) * 100).toFixed(1) + "%" : "—";
        return `<tr><td>${_escapeHtml(fips)}</td><td>${_escapeHtml(name)}</td><td>${_escapeHtml(mean)}</td><td>${_escapeHtml(mx)}</td><td>${_escapeHtml(ratio)}</td><td>${_escapeHtml(top10)}</td></tr>`;
    }).join("");

    const tables = `
        <div class="exp-tables">
            <div class="exp-table-wrap">
                <div class="exp-table-wrap__title">Exp2 – County Expected Annual Loss (top 10)</div>
                <table class="exp-table" aria-label="Experiment 2 county EAL ranking">
                    <thead><tr><th>#</th><th>County</th><th>Name</th><th>county_eal (sum)</th><th>mean risk</th></tr></thead>
                    <tbody>${ealRows || `<tr><td colspan="5">—</td></tr>`}</tbody>
                </table>
            </div>
            <div class="exp-table-wrap">
                <div class="exp-table-wrap__title">Exp5 – Within-county heterogeneity (selected)</div>
                <table class="exp-table" aria-label="Experiment 5 within-county heterogeneity">
                    <thead><tr><th>County</th><th>Name</th><th>Block mean</th><th>Block max</th><th>Max/Mean</th><th>Top-10% share</th></tr></thead>
                    <tbody>${hetRows || `<tr><td colspan="6">—</td></tr>`}</tbody>
                </table>
            </div>
        </div>
    `;

    host.innerHTML = cards + tables;
}

function prefetchPackagedCounties(manifest, currentId) {
    const ids = manifest.prefetched_county_ids || [];
    for (const id of ids) {
        const url = manifest.datasets && manifest.datasets[id];
        if (!url || id === currentId) continue;
        fetch(url).catch(() => {});
    }
}

function loadCounty(id, manifest) {
    const url = manifest.datasets && manifest.datasets[id];
    const msg = d3.select("#countyMessage");
    if (!url) {
        geoData = { type: "FeatureCollection", features: [] };
        mapZoomTransform = d3.zoomIdentity;
        fitProjectionToGeo(getCellDimensions().width, getCellDimensions().height);
        msg.text(
            "No packaged block-level GeoJSON for this county yet. " +
            "Add data/processed/counties/" + id + "/blocks.geojson and register it in data/county_manifest.json, " +
            "or choose another county."
        );
        return Promise.resolve();
    }
    msg.text("");
    return d3.json(url).then(data => {
        mapZoomTransform = d3.zoomIdentity;
        geoData = data;
        fitProjectionToGeo(getCellDimensions().width, getCellDimensions().height);
    }).catch(err => {
        mapZoomTransform = d3.zoomIdentity;
        geoData = { type: "FeatureCollection", features: [] };
        fitProjectionToGeo(getCellDimensions().width, getCellDimensions().height);
        msg.text("Failed to load county GeoJSON: " + (err && err.message ? err.message : String(err)));
        console.error(err);
    });
}

function populateCountySelect(list, manifest) {
    const sel = document.getElementById("county");
    const prefetched = new Set(manifest.prefetched_county_ids || []);
    sel.innerHTML = "";

    function _isCaliforniaCountyId(id) {
        const s = String(id || "").trim();
        return s.length === 5 && s.startsWith("06");
    }

    function _normalizeCountyLabel(label) {
        // county_list.json currently uses "State - County Name" (e.g., "California - Los Angeles County")
        // but we want just "Los Angeles County".
        const s = String(label || "").trim();
        const parts = s.split(" - ");
        const tail = parts.length >= 2 ? parts[parts.length - 1] : s;
        return tail.replace(/\s*\(.*?\)\s*/g, "").trim();
    }

    const caCounties = (list.counties || []).filter((c) => _isCaliforniaCountyId(c.id));
    for (const c of caCounties) {
        const o = document.createElement("option");
        o.value = c.id;
        o.textContent = _normalizeCountyLabel(c.label);
        if (prefetched.has(c.id)) o.className = "prefetched";
        sel.appendChild(o);
    }
    const datasets = manifest.datasets || {};
    let defaultId = null;
    for (const id of manifest.prefetched_county_ids || []) {
        if (datasets[id]) {
            defaultId = id;
            break;
        }
    }
    if (!defaultId && Object.keys(datasets).length) {
        defaultId = Object.keys(datasets)[0];
    }
    const fallback = caCounties[0] && caCounties[0].id;
    const start = defaultId || fallback;
    if (start) sel.value = start;
    return start;
}

Promise.all([
    d3.json("data/county_list.json"),
    d3.json("data/county_manifest.json"),
    d3.json("data/validation/merged_all_counties.json").catch(() => null),
    d3.json("data/validation/merged_06007_06073.json").catch(() => null)
]).then(([list, manifest, mergedAll, mergedLegacy]) => {
    countyManifest = manifest;
    _mergedAllUiDoc = mergedAll || null;
    populateMapCalcSections();
    const startId = populateCountySelect(list, manifest);
    return loadCounty(startId, manifest).then(() => {
        prefetchPackagedCounties(manifest, startId);
        // Ensure initial render matches the checkbox default state (some browsers restore
        // checkbox state without triggering a "change" event).
        const detail = document.getElementById("mapDetail");
        if (detail) applyMapDetailMode(!!detail.checked);
        else renderAll();
        renderExperimentsDashboard();
    });
}).catch(err => {
    const msg = document.getElementById("countyMessage");
    if (msg) {
        msg.textContent =
            "Could not load county list or manifest. Ensure data/county_list.json and data/county_manifest.json exist (run scripts/build_county_list.py for the list). " +
            (err && err.message ? err.message : String(err));
    }
    console.error(err);
});

d3.select("#county").on("change", function () {
    const id = this.value;
    loadCounty(id, countyManifest).then(() => {
        renderAll();
        renderExperimentsDashboard();
    });
});

d3.select("#mapDetail").on("change", function () {
    applyMapDetailMode(!!this.checked);
});

// Synced zoom sliders (one per panel)
try {
    document.querySelectorAll("input.zoom-slider").forEach((s) => {
        s.addEventListener("input", () => {
            if (_zoomSliderSyncing) return;
            setZoomKFromSliderValue(s.value);
        });
    });
    updateZoomSliderFromTransform();
} catch (e) {}
