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
    risk_score: ["#FEE0D2", "#FC9272", "#D73027"],
    hazard_score: ["#FEE8C8", "#FDBB84", "#F46D43"],
    exposure_score: ["#FFF7BC", "#FEC44F", "#FDAE61"],
    vulnerability_score: ["#EFEDF5", "#BCBDDC", "#8073AC"],
    resilience_score: ["#E5F5E0", "#74C476", "#1A9850"],
    eal_norm: ["#DEEBF7", "#9ECAE1", "#4575B4"],
};

/** Darkest stop in each choropleth ramp — used for linked UI/tooltip accents. */
function darkestColor(metric) {
    const ramp = METRIC_COLOR_RAMPS[metric] || METRIC_COLOR_RAMPS.risk_score;
    return ramp[ramp.length - 1];
}

function tooltipAccent(metric, label, valueHtml) {
    const c = darkestColor(metric);
    return `<span style="color:${c}"><b>${label}</b> ${valueHtml}</span>`;
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
    const rs = (v) => (v != null && Number.isFinite(v) ? Number(v).toFixed(4) : "NA");
    let html = `
${tooltipAccent("risk_score", "Risk:", rs(p.risk_score))}<br/>
${tooltipAccent("hazard_score", "Hazard:", rs(p.hazard_score))}<br/>
${tooltipAccent("exposure_score", "Exposure:", rs(p.exposure_score))}<br/>
${tooltipAccent("vulnerability_score", "Vulnerability:", rs(p.vulnerability_score))}<br/>
${tooltipAccent("resilience_score", "Resilience:", rs(p.resilience_score))}<br/>
<hr/>
${tooltipAccent("exposure_score", "Population:", _formatValue(p, "exposure_population", v => Number(v).toLocaleString()))}<br/>
${tooltipAccent("exposure_score", "Housing units:", _formatValue(p, "exposure_housing", v => Math.round(v).toLocaleString()))}<br/>
${tooltipAccent("exposure_score", "Building value:", _formatValue(p, "exposure_building_value", v => "$" + Math.round(v).toLocaleString()))}<br/>
${tooltipAccent("eal_norm", "EAL (USD):", _formatValue(p, "eal", v => "$" + Math.round(v).toLocaleString()))}<br/>
${tooltipAccent("eal_norm", "EAL (normalized):", _formatValue(p, "eal_norm", v => Number(v).toFixed(4)))}
`;

    if (DEBUG_MODE) {
        const ch = darkestColor("hazard_score");
        const cv = darkestColor("vulnerability_score");
        const cr = darkestColor("resilience_score");
        html += `
<hr/>
<b>Diagnostics:</b><br/>`;
        let diag = p.diagnostics;
        if (typeof diag === "string") {
            try { diag = JSON.parse(diag); } catch (e) { diag = {}; }
        }
        if (diag && typeof diag === "object" && Object.keys(diag).length > 0) {
            for (const [field, issues] of Object.entries(diag)) {
                const arr = Array.isArray(issues) ? issues : [issues];
                html += `<b>${field}:</b> ${arr.join("; ")}<br/>`;
            }
        } else {
            html += "No validation issues.<br/>";
        }
        html += `
<hr/>
<span style="color:${ch}"><b>Feature values (hazard inputs):</b></span><br/>
<span style="color:${ch}"><b>hazard_wildfire:</b> ${_formatValue(p, "hazard_wildfire", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${ch}"><b>hazard_vegetation:</b> ${_formatValue(p, "hazard_vegetation", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${ch}"><b>hazard_forest_distance:</b> ${_formatValue(p, "hazard_forest_distance", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cv}"><b>Vulnerability inputs:</b></span><br/>
<span style="color:${cv}"><b>vuln_poverty:</b> ${_formatValue(p, "vuln_poverty", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cv}"><b>vuln_elderly:</b> ${_formatValue(p, "vuln_elderly", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cv}"><b>vuln_vehicle_access:</b> ${_formatValue(p, "vuln_vehicle_access", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cr}"><b>Resilience inputs:</b></span><br/>
<span style="color:${cr}"><b>res_fire_station_dist:</b> ${_formatValue(p, "res_fire_station_dist", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cr}"><b>res_hospital_dist:</b> ${_formatValue(p, "res_hospital_dist", v => Number(v).toFixed(4))}</span><br/>
<span style="color:${cr}"><b>res_road_access:</b> ${_formatValue(p, "res_road_access", v => Number(v).toFixed(4))}</span>
`;
    }

    return html;
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
