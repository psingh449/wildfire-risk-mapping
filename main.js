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

function _fmtScore2(v) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "NA";
    return n.toFixed(2);
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


function colorScaleForMetric(metric) {
    const stops = METRIC_COLOR_RAMPS[metric] || METRIC_COLOR_RAMPS.risk_score;
    return d3.scaleSequential(d3.interpolateRgbBasis(stops)).domain([0, 1]);
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
        _tooltipRowCols("risk_score", "Risk:", _fmtScore2(p.risk_score), "", false),
        _tooltipRowCols("hazard_score", "Hazard:", _fmtScore2(p.hazard_score), "", false),
        _tooltipRowCols("exposure_score", "Exposure:", _fmtScore2(p.exposure_score), "", false),
        _tooltipRowCols("vulnerability_score", "Vulnerability:", _fmtScore2(p.vulnerability_score), "", false),
        _tooltipRowCols("resilience_score", "Resilience:", _fmtScore2(p.resilience_score), "", false),
        _tooltipRowCols("eal_norm", "EL (eal_norm):", _fmtScore2(p.eal_norm), "", false),
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
            rowFromFormatted("hazard_score", "hazard_wildfire:", _formatValue(p, "hazard_wildfire", v => Number(v).toFixed(2)), false),
            rowFromFormatted("hazard_score", "hazard_vegetation:", _formatValue(p, "hazard_vegetation", v => Number(v).toFixed(2)), false),
            rowFromFormatted("hazard_score", "hazard_forest_distance:", _formatValue(p, "hazard_forest_distance", v => Number(v).toFixed(2)), false),
        ].join("");

        const vulnDebug = [
            rowFromFormatted("vulnerability_score", "vuln_poverty:", _formatValue(p, "vuln_poverty", v => Number(v).toFixed(2)), false),
            rowFromFormatted("vulnerability_score", "vuln_elderly:", _formatValue(p, "vuln_elderly", v => Number(v).toFixed(2)), false),
            rowFromFormatted("vulnerability_score", "vuln_vehicle_access:", _formatValue(p, "vuln_vehicle_access", v => Number(v).toFixed(2)), false),
        ].join("");

        const resDebug = [
            rowFromFormatted("resilience_score", "res_fire_station_dist:", _formatValue(p, "res_fire_station_dist", v => Number(v).toFixed(2)), false),
            rowFromFormatted("resilience_score", "res_hospital_dist:", _formatValue(p, "res_hospital_dist", v => Number(v).toFixed(2)), false),
            rowFromFormatted("resilience_score", "res_road_access:", _formatValue(p, "res_road_access", v => Number(v).toFixed(2)), false),
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

    for (const { panelId, metric } of MAP_PANELS) {
        const mapSvg = d3.select(`#${panelId} svg.map-svg`);
        const legendSvg = d3.select(`#${panelId} svg.legend-svg`);
        if (mapSvg.empty()) continue;

        const color = colorScaleForMetric(metric);
        const gradientId = `legend-gradient-${metric}`;

        mapSvg.selectAll("*").remove();
        if (!legendSvg.empty()) legendSvg.selectAll("*").remove();

        mapSvg.selectAll("path")
            .data((geoData && geoData.features) ? geoData.features : [])
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
            .attr("stop-color", d => color(d));

        const legendGroup = legendSvg.append("g")
            .attr("transform", `translate(${gx}, 8)`);

        legendGroup.append("rect")
            .attr("width", legendWidth)
            .attr("height", legendBarH)
            .style("fill", `url(#${gradientId})`);

        const scale = d3.scaleLinear()
            .domain([0, 1])
            .range([0, legendWidth]);

        const axis = d3.axisBottom(scale)
            .ticks(5)
            .tickFormat(d3.format(".1f"));

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
        geoData = data;
        fitProjectionToGeo(getCellDimensions().width, getCellDimensions().height);
    }).catch(err => {
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
