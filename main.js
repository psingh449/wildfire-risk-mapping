const svg = d3.select("svg");
const width = +svg.attr("width");
const height = +svg.attr("height");

const DEFAULT_METRIC = "risk_score";

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

function sourceBadge(isReal) {
    const cls = isReal ? "badge badge-real" : "badge badge-dummy";
    const txt = isReal ? "REAL" : "DUMMY";
    return `<span class="${cls}">${txt}</span>`;
}

function isRealField(p, key) {
    return p[key + "_source"] === "REAL";
}

const projection = d3.geoMercator();
const path = d3.geoPath().projection(projection);

let geoData;
let countyManifest;
let DEBUG_MODE = true;

const descriptions = {
    risk_score: "Overall wildfire risk combining hazard, exposure, vulnerability, and resilience.",
    hazard_score: "Likelihood and intensity of wildfire occurrence.",
    exposure_score: "Population and assets exposed to wildfire.",
    vulnerability_score: "Sensitivity of the population to wildfire impacts.",
    resilience_score: "Ability to respond to and recover from wildfire events.",
    eal_norm: "Expected Annual Loss (EAL), min–max scaled (eal_norm) for mapping; raw EAL is in USD."
};

const tooltip = d3.select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

function buildTooltip(p) {
    const bval = p.exposure_building_value != null ? Math.round(p.exposure_building_value) : 0;
    let html = `
<b>Risk:</b> ${p.risk_score?.toFixed(4) ?? "NA"}<br/>
<b>Hazard:</b> ${p.hazard_score?.toFixed(4) ?? "NA"}<br/>
<b>Exposure:</b> ${p.exposure_score?.toFixed(4) ?? "NA"}<br/>
<b>Vulnerability:</b> ${p.vulnerability_score?.toFixed(4) ?? "NA"}<br/>
<b>Resilience:</b> ${p.resilience_score?.toFixed(4) ?? "NA"}<br/>
<hr/>
<b>Population:</b> ${p.exposure_population ?? "NA"} ${sourceBadge(isRealField(p, "exposure_population"))}<br/>
<b>Building value (ACS × housing):</b> $${bval.toLocaleString()} ${sourceBadge(isRealField(p, "exposure_building_value"))}<br/>
<b>EAL (USD):</b> $${Math.round(p.eal ?? 0).toLocaleString()}<br/>
<b>EAL (normalized):</b> ${p.eal_norm?.toFixed(4) ?? "NA"}
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
hazard_wildfire: ${p.hazard_wildfire?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "hazard_wildfire"))}<br/>
hazard_vegetation: ${p.hazard_vegetation?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "hazard_vegetation"))}<br/>
hazard_forest_distance: ${p.hazard_forest_distance?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "hazard_forest_distance"))}<br/>
exposure_housing: ${p.exposure_housing?.toFixed(0) ?? "NA"} ${sourceBadge(isRealField(p, "exposure_housing"))}<br/>
vuln_poverty: ${p.vuln_poverty?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "vuln_poverty"))}<br/>
vuln_elderly: ${p.vuln_elderly?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "vuln_elderly"))}<br/>
vuln_vehicle_access: ${p.vuln_vehicle_access?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "vuln_vehicle_access"))}<br/>
res_fire_station_dist: ${p.res_fire_station_dist?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "res_fire_station_dist"))}<br/>
res_hospital_dist: ${p.res_hospital_dist?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "res_hospital_dist"))}<br/>
res_road_access: ${p.res_road_access?.toFixed(4) ?? "NA"} ${sourceBadge(isRealField(p, "res_road_access"))}
`;
    }

    return html;
}

function fitProjectionToGeo() {
    if (geoData && geoData.features && geoData.features.length > 0) {
        projection.fitSize([width, height], geoData);
    } else {
        projection
            .scale(1)
            .translate([width / 2, height / 2]);
        const outline = { type: "Feature", geometry: { type: "Polygon", coordinates: [[[-125, 24], [-66, 24], [-66, 50], [-125, 50], [-125, 24]]] } };
        projection.fitSize([width, height], outline);
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
        fitProjectionToGeo();
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
        fitProjectionToGeo();
    }).catch(err => {
        geoData = { type: "FeatureCollection", features: [] };
        fitProjectionToGeo();
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
        const metric = d3.select("#metric").property("value") || DEFAULT_METRIC;
        render(metric);
        updateDescription(metric);
    });
}).catch(err => {
    document.getElementById("description").textContent =
        "Could not load county list or manifest. Ensure data/county_list.json and data/county_manifest.json exist (run scripts/build_county_list.py for the list).";
    document.getElementById("countyMessage").textContent = String(err && err.message ? err.message : err);
    console.error(err);
});

d3.select("#county").on("change", function () {
    const id = this.value;
    loadCounty(id, countyManifest).then(() => {
        const metric = d3.select("#metric").property("value") || DEFAULT_METRIC;
        render(metric);
        updateDescription(metric);
    });
});

d3.select("#metric").on("change", function () {
    const metric = this.value;
    render(metric);
    updateDescription(metric);
});

d3.select("#reset").on("click", function () {
    d3.select("#metric").property("value", DEFAULT_METRIC);
    render(DEFAULT_METRIC);
    updateDescription(DEFAULT_METRIC);
});

d3.select("#debugToggle").on("change", function () {
    DEBUG_MODE = this.checked;
});

function updateDescription(metric) {
    d3.select("#description").text(descriptions[metric] || "");
}

function render(metric) {
    const color = colorScaleForMetric(metric);

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

    const legendWidth = 250;
    const legendHeight = 12;

    const legendGroup = svg.append("g")
        .attr("transform", "translate(20,20)");

    const gradientId = "legend-gradient";

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
        .text(metric.toUpperCase());

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
