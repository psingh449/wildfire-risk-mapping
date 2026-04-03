const svg = d3.select("svg");
const width = +svg.attr("width");
const height = +svg.attr("height");

const DEFAULT_METRIC = "risk_score";

// Badge helpers
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
let DEBUG_MODE = true;

const descriptions = {
    risk_score: "Overall wildfire risk combining hazard, exposure, vulnerability, and resilience.",
    hazard_score: "Likelihood and intensity of wildfire occurrence.",
    exposure_score: "Population and assets exposed to wildfire.",
    vulnerability_score: "Sensitivity of the population to wildfire impacts.",
    resilience_score: "Ability to respond to and recover from wildfire events.",
    eal_norm: "Expected Annual Loss (economic risk proxy based on property value and risk)."
};

// Tooltip
const tooltip = d3.select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

function buildTooltip(p) {

    let html = `
<b>Risk:</b> ${p.risk_score?.toFixed(2) ?? "NA"}<br/>
<b>Hazard:</b> ${p.hazard_score?.toFixed(2) ?? "NA"}<br/>
<b>Exposure:</b> ${p.exposure_score?.toFixed(2) ?? "NA"}<br/>
<b>Vulnerability:</b> ${p.vulnerability_score?.toFixed(2) ?? "NA"}<br/>
<b>Resilience:</b> ${p.resilience_score?.toFixed(2) ?? "NA"}<br/>
<hr/>
<b>Population:</b> ${p.exposure_population ?? "NA"} ${sourceBadge(isRealField(p, "exposure_population"))}<br/>
<b>Building Value:</b> $${Math.round(p.building_value_est ?? 0).toLocaleString()} ${sourceBadge(isRealField(p, "exposure_building_value"))}<br/>
<b>EAL:</b> $${Math.round(p.eal ?? 0).toLocaleString()} ${sourceBadge(isRealField(p, "eal"))}
`;

    if (DEBUG_MODE) {
        html += `
<hr/>
<b>DEBUG:</b><br/>
hazard_wildfire: ${p.hazard_wildfire?.toFixed(2) ?? "NA"}<br/>
hazard_vegetation: ${p.hazard_vegetation?.toFixed(2) ?? "NA"}<br/>
hazard_forest_distance: ${p.hazard_forest_distance?.toFixed(2) ?? "NA"}<br/>
<br/>
exposure_population: ${p.exposure_population ?? "NA"}<br/>
exposure_housing: ${p.exposure_housing?.toFixed(0) ?? "NA"}<br/>
exposure_building_value: ${p.exposure_building_value?.toFixed(0) ?? "NA"}<br/>
<br/>
vuln_poverty: ${p.vuln_poverty?.toFixed(2) ?? "NA"}<br/>
vuln_elderly: ${p.vuln_elderly?.toFixed(2) ?? "NA"}<br/>
vuln_vehicle_access: ${p.vuln_vehicle_access?.toFixed(2) ?? "NA"}<br/>
<br/>
res_fire_station_dist: ${p.res_fire_station_dist?.toFixed(2) ?? "NA"}<br/>
res_hospital_dist: ${p.res_hospital_dist?.toFixed(2) ?? "NA"}<br/>
res_road_access: ${p.res_road_access?.toFixed(2) ?? "NA"}
`;
    }

    return html;
}

// Load data
d3.json("data/processed/blocks.geojson").then(data => {
    geoData = data;
    projection.fitSize([width, height], geoData);
    render(DEFAULT_METRIC);
    updateDescription(DEFAULT_METRIC);
});

// Dropdown
d3.select("#metric").on("change", function () {
    const metric = this.value;
    render(metric);
    updateDescription(metric);
});

// Reset
d3.select("#reset").on("click", function () {
    d3.select("#metric").property("value", DEFAULT_METRIC);
    render(DEFAULT_METRIC);
    updateDescription(DEFAULT_METRIC);
});

// Debug toggle
d3.select("#debugToggle").on("change", function () {
    DEBUG_MODE = this.checked;
});

function updateDescription(metric) {
    d3.select("#description").text(descriptions[metric]);
}

function render(metric) {

    const color = d3.scaleSequential(d3.interpolateReds)
        .domain([0, 1]);

    svg.selectAll("*").remove();

    svg.selectAll("path")
        .data(geoData.features)
        .join("path")
        .attr("d", path)
        .attr("fill", d => color(d.properties[metric]))
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

    // Legend
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