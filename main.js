const MAP_PANELS = [
    { panelId: "map-panel-eal", metric: "eal_norm", legendLabel: "EL (eal_norm)" },
    { panelId: "map-panel-risk", metric: "risk_score", legendLabel: "RISC (risk_score)" },
    { panelId: "map-panel-hazard", metric: "hazard_score", legendLabel: "HAZARD" },
    { panelId: "map-panel-exposure", metric: "exposure_score", legendLabel: "EXPOSURE" },
    { panelId: "map-panel-vulnerability", metric: "vulnerability_score", legendLabel: "VULNERABILITY" },
    { panelId: "map-panel-resilience", metric: "resilience_score", legendLabel: "RESILIENCE" },
];

const METRIC_COLOR_RAMPS = {
    risk_score: ["#FEE0D2", "#FC9272", "#D73027"],
    hazard_score: ["#FEE8C8", "#FDBB84", "#F46D43"],
    exposure_score: ["#FFF7BC", "#FEC44F", "#FDAE61"],
    vulnerability_score: ["#EFEDF5", "#BCBDDC", "#8073AC"],
    resilience_score: ["#E5F5E0", "#74C476", "#1A9850"],
    eal_norm: ["#DEEBF7", "#9ECAE1", "#4575B4"],
};

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
    let html = `
<b>Risk:</b> ${p.risk_score?.toFixed(4) ?? "NA"}<br/>
<b>Hazard:</b> ${p.hazard_score?.toFixed(4) ?? "NA"}<br/>
<b>Exposure:</b> ${p.exposure_score?.toFixed(4) ?? "NA"}<br/>
<b>Vulnerability:</b> ${p.vulnerability_score?.toFixed(4) ?? "NA"}<br/>
<b>Resilience:</b> ${p.resilience_score?.toFixed(4) ?? "NA"}<br/>
<hr/>
<b>Population:</b> ${_formatValue(p, "exposure_population", v => Number(v).toLocaleString())}<br/>
<b>Housing units:</b> ${_formatValue(p, "exposure_housing", v => Math.round(v).toLocaleString())}<br/>
<b>Building value:</b> ${_formatValue(p, "exposure_building_value", v => "$" + Math.round(v).toLocaleString())}<br/>
<b>EAL (USD):</b> ${_formatValue(p, "eal", v => "$" + Math.round(v).toLocaleString())}<br/>
<b>EAL (normalized):</b> ${_formatValue(p, "eal_norm", v => Number(v).toFixed(4))}
`;

    if (DEBUG_MODE) {
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
<b>Feature values (debug):</b><br/>
hazard_wildfire: ${_formatValue(p, "hazard_wildfire", v => Number(v).toFixed(4))}<br/>
hazard_vegetation: ${_formatValue(p, "hazard_vegetation", v => Number(v).toFixed(4))}<br/>
hazard_forest_distance: ${_formatValue(p, "hazard_forest_distance", v => Number(v).toFixed(4))}<br/>
vuln_poverty: ${_formatValue(p, "vuln_poverty", v => Number(v).toFixed(4))}<br/>
vuln_elderly: ${_formatValue(p, "vuln_elderly", v => Number(v).toFixed(4))}<br/>
vuln_vehicle_access: ${_formatValue(p, "vuln_vehicle_access", v => Number(v).toFixed(4))}<br/>
res_fire_station_dist: ${_formatValue(p, "res_fire_station_dist", v => Number(v).toFixed(4))}<br/>
res_hospital_dist: ${_formatValue(p, "res_hospital_dist", v => Number(v).toFixed(4))}<br/>
res_road_access: ${_formatValue(p, "res_road_access", v => Number(v).toFixed(4))}
`;
    }

    return html;
}

function attachTooltipHandlers(selection) {
    selection
        .on("mouseover", function (event, d) {
            const p = d.properties;
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
        .on("mouseout", function () {
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
        const w = +first.getAttribute("width") || 440;
        const h = +first.getAttribute("height") || 280;
        return { width: w, height: h };
    }
    return { width: 440, height: 280 };
}

function renderAll() {
    const { width: mapW, height: mapH } = getCellDimensions();
    fitProjectionToGeo(mapW, mapH);

    for (const { panelId, metric, legendLabel } of MAP_PANELS) {
        const svg = d3.select(`#${panelId} svg.map-svg`);
        if (svg.empty()) continue;

        const color = colorScaleForMetric(metric);
        const gradientId = `legend-gradient-${metric}`;

        svg.selectAll("*").remove();

        svg.selectAll("path")
            .data((geoData && geoData.features) ? geoData.features : [])
            .join("path")
            .attr("d", path)
            .attr("fill", d => {
                const v = d.properties[metric];
                return v != null && !isNaN(v) ? color(v) : "#ccc";
            })
            .attr("stroke", "#333")
            .call(attachTooltipHandlers);

        const legendWidth = 250;
        const legendHeight = 12;

        const legendGroup = svg.append("g")
            .attr("transform", "translate(20,20)");

        const defs = svg.append("defs");

        const gradient = defs.append("linearGradient")
            .attr("id", gradientId);

        gradient.selectAll("stop")
            .data(d3.range(0, 1.01, 0.05))
            .enter()
            .append("stop")
            .attr("offset", d => d * 100 + "%")
            .attr("stop-color", d => color(d));

        legendGroup.append("text")
            .attr("y", -8)
            .attr("class", "legend-title")
            .text(legendLabel);

        legendGroup.append("rect")
            .attr("width", legendWidth)
            .attr("height", legendHeight)
            .style("fill", `url(#${gradientId})`);

        const scale = d3.scaleLinear()
            .domain([0, 1])
            .range([0, legendWidth]);

        const axis = d3.axisBottom(scale)
            .ticks(5)
            .tickFormat(d3.format(".1f"));

        legendGroup.append("g")
            .attr("transform", `translate(0,${legendHeight})`)
            .call(axis);
    }
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
