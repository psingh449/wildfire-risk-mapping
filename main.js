const MAP_PANELS = [
    { panelId: "map-panel-eal", metric: "eal_norm" },
    { panelId: "map-panel-risk", metric: "risk_score" },
    { panelId: "map-panel-hazard", metric: "hazard_score" },
    { panelId: "map-panel-exposure", metric: "exposure_score" },
    { panelId: "map-panel-vulnerability", metric: "vulnerability_score" },
    { panelId: "map-panel-resilience", metric: "resilience_score" },
];

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
    if (metric === "risk_score") {
        if (n < 0.01) return n.toFixed(3);
        if (n < 0.1) return n.toFixed(2);
    }
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
    if ((key === "eal" || key === "eal_norm") && DEBUG_MODE) {
        return _debugTagEalFamily(p, key);
    }
    const q = _qualityFor(p, key);
    const prov = p[key + "_provenance"] || "";
    if (!DEBUG_MODE) return "";
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
    const base = fmt(v);
    const star = (q === "ESTIMATED" || q === "PROXY") ? "*" : "";
    const tag = _debugTag(p, key);
    return `${base}${star}${tag ? " " + tag : ""}`;
}

const projection = d3.geoMercator();
const path = d3.geoPath().projection(projection);

/** Shared across all six maps; use identity after each county load. */
let mapZoomTransform = d3.zoomIdentity;
let _mapZoomSyncing = false;

const mapZoom = d3
    .zoom()
    .scaleExtent([0.35, 48])
    .on("zoom", (event) => {
        if (_mapZoomSyncing) return;
        mapZoomTransform = event.transform;
        d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
        updateZoomSliderFromTransform();
        _mapZoomSyncing = true;
        d3.selectAll("svg.map-svg").each(function () {
            d3.select(this).call(mapZoom.transform, mapZoomTransform);
        });
        _mapZoomSyncing = false;
    });

let _mapZoomInstalled = false;

// --- Zoom slider (shared, flush right) ---
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 48;
const zoomKToSlider = d3.scaleLog().domain([ZOOM_MIN, ZOOM_MAX]).range([0, 100]).clamp(true);
const sliderToZoomK = d3.scaleLog().domain([1, 100]).range([ZOOM_MIN, ZOOM_MAX]).clamp(true);
let _zoomSliderSyncing = false;

function updateZoomSliderFromTransform() {
    const el = document.getElementById("zoomSlider");
    if (!el) return;
    if (_zoomSliderSyncing) return;
    const k = mapZoomTransform && Number.isFinite(mapZoomTransform.k) ? mapZoomTransform.k : 1;
    const v = zoomKToSlider(k);
    _zoomSliderSyncing = true;
    el.value = String(Math.round(v));
    _zoomSliderSyncing = false;
}

function setZoomKFromSliderValue(rawValue) {
    const v = Number(rawValue);
    if (!Number.isFinite(v)) return;
    const safe = Math.min(100, Math.max(1, v)); // avoid log(0)
    const newK = sliderToZoomK(safe);
    const { width: w, height: h } = getCellDimensions();
    const cx = w / 2;
    const cy = h / 2;
    // Keep the current screen center stable while changing scale.
    const cur = mapZoomTransform || d3.zoomIdentity;
    const next = d3.zoomIdentity
        .translate(cx, cy)
        .scale(newK)
        .translate(-cx, -cy)
        .translate(cur.x, cur.y);

    mapZoomTransform = next;
    d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
    _mapZoomSyncing = true;
    d3.selectAll("svg.map-svg").call(mapZoom.transform, mapZoomTransform);
    _mapZoomSyncing = false;
}

function resetMapView() {
    mapZoomTransform = d3.zoomIdentity;
    d3.selectAll("svg.map-svg g.map-zoom-layer").attr("transform", mapZoomTransform);
    updateZoomSliderFromTransform();
    _mapZoomSyncing = true;
    d3.selectAll("svg.map-svg").each(function () {
        d3.select(this).call(mapZoom.transform, mapZoomTransform);
    });
    _mapZoomSyncing = false;
}

let geoData;
let countyManifest;
const _params = new URLSearchParams(window.location.search);
let DEBUG_MODE = _params.get("debug") === "1" || _params.get("debug") === "true";

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
        _tooltipRowCols("eal_norm", "EL (eal_norm):", _fmtPanelTooltip(p.eal_norm, "eal_norm"), "", false),
    ].join("");

    const bigHtml = [
        rowFromFormatted("exposure_score", "Population:", _formatValue(p, "exposure_population", v => Number(v).toLocaleString()), true),
        rowFromFormatted("exposure_score", "Housing units:", _formatValue(p, "exposure_housing", v => Math.round(v).toLocaleString()), true),
        rowFromFormatted("exposure_score", "Building value:", _formatValue(p, "exposure_building_value", v => "$" + Math.round(v).toLocaleString()), true),
        rowFromFormatted("eal_norm", "EAL (USD):", _formatValue(p, "eal", v => "$" + Math.round(v).toLocaleString()), false),
    ].join("");

    const parts = [scoresHtml, `<hr class="tooltip-hr"/>`, bigHtml];

    if (DEBUG_MODE) {
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
            rowFromFormatted("vulnerability_score", "vuln_vehicle_access:", _formatValue(p, "vuln_vehicle_access", v => Number(v).toFixed(1)), false),
        ].join("");

        const resDebug = [
            rowFromFormatted("resilience_score", "res_fire_station_dist:", _formatValue(p, "res_fire_station_dist", v => Number(v).toFixed(1)), false),
            rowFromFormatted("resilience_score", "res_hospital_dist:", _formatValue(p, "res_hospital_dist", v => Number(v).toFixed(1)), false),
            rowFromFormatted("resilience_score", "res_road_access:", _formatValue(p, "res_road_access", v => Number(v).toFixed(1)), false),
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
    }

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
    if (geoData && geoData.features && geoData.features.length > 0) {
        projection.fitSize([mapWidth, mapHeight], geoData);
    } else {
        projection
            .scale(1)
            .translate([mapWidth / 2, mapHeight / 2]);
        const outline = { type: "Feature", geometry: { type: "Polygon", coordinates: [[[-125, 24], [-66, 24], [-66, 50], [-125, 50], [-125, 24]]] } };
        projection.fitSize([mapWidth, mapHeight], outline);
    }
}

function getCellDimensions() {
    const first = document.querySelector("#map-panel-eal svg.map-svg");
    if (first) {
        const w = +first.getAttribute("width") || 320;
        const h = +first.getAttribute("height") || 220;
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

        const legendWidth = 250;
        const legendBarH = 12;
        const svgW = +legendSvg.attr("width") || 440;
        const gx = (svgW - legendWidth) / 2;
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
            .tickFormat(tickFmt);

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
    for (const c of list.counties) {
        const o = document.createElement("option");
        o.value = c.id;
        o.textContent = c.label;
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
    const fallback = list.counties[0] && list.counties[0].id;
    const start = defaultId || fallback;
    if (start) sel.value = start;
    return start;
}

Promise.all([
    d3.json("data/county_list.json"),
    d3.json("data/county_manifest.json")
]).then(([list, manifest]) => {
    countyManifest = manifest;
    const startId = populateCountySelect(list, manifest);
    return loadCounty(startId, manifest).then(() => {
        prefetchPackagedCounties(manifest, startId);
        renderAll();
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
    });
});

d3.select("#debugToggle").on("change", function () {
    DEBUG_MODE = this.checked;
});

try {
    const t = document.getElementById("debugToggle");
    if (t) t.checked = DEBUG_MODE;
} catch (e) {}

// Shared zoom slider
try {
    const s = document.getElementById("zoomSlider");
    if (s) {
        s.addEventListener("input", () => {
            if (_zoomSliderSyncing) return;
            setZoomKFromSliderValue(s.value);
        });
        // Initialize from identity
        updateZoomSliderFromTransform();
    }
} catch (e) {}
