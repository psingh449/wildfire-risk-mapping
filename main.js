const svg = d3.select("svg");
const width = +svg.attr("width");
const height = +svg.attr("height");

const projection = d3.geoIdentity().reflectY(true);
const path = d3.geoPath().projection(projection);

let geoData;

const descriptions = {
    risk_score: "Overall wildfire risk combining hazard, exposure, vulnerability, and resilience.",
    hazard_score: "Likelihood and intensity of wildfire occurrence.",
    exposure_score: "Amount of population and assets exposed to wildfire.",
    vulnerability_score: "Sensitivity of the population to wildfire impacts.",
    resilience_score: "Ability to respond to and recover from wildfire events."
};

const tooltip = d3.select("body")
  .append("div")
  .attr("class", "tooltip")
  .style("opacity", 0);

d3.json("data/processed/blocks.geojson").then(data => {
    geoData = data;
    projection.fitSize([width, height], geoData);
    render("risk_score");
    updateDescription("risk_score");
});

d3.select("#metric").on("change", function() {
    const metric = this.value;
    render(metric);
    updateDescription(metric);
});

function updateDescription(metric) {
    d3.select("#description")
        .text(descriptions[metric]);
}

function render(metric) {

    const color = d3.scaleSequential(d3.interpolateReds)
        .domain([0,1]);

    svg.selectAll("*").remove();

    svg.selectAll("path")
        .data(geoData.features)
        .join("path")
        .attr("d", path)
        .attr("fill", d => color(d.properties[metric]))
        .attr("stroke", "#333")
        .on("mouseover", function(event, d) {
            const p = d.properties;

            tooltip.transition().duration(200).style("opacity", .9);
            tooltip.html(`
                <b>Risk:</b> ${p.risk_score.toFixed(2)}<br/>
                <b>Hazard:</b> ${p.hazard_score.toFixed(2)}<br/>
                <b>Exposure:</b> ${p.exposure_score.toFixed(2)}<br/>
                <b>Vulnerability:</b> ${p.vulnerability_score.toFixed(2)}<br/>
                <b>Resilience:</b> ${p.resilience_score.toFixed(2)}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 20) + "px");
        })
        .on("mousemove", function(event) {
            tooltip
              .style("left", (event.pageX + 10) + "px")
              .style("top", (event.pageY - 20) + "px");
        })
        .on("mouseout", function() {
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
        .domain([0,1])
        .range([0, legendWidth]);

    const axis = d3.axisBottom(scale)
        .ticks(5)
        .tickFormat(d3.format(".1f"));

    legendGroup.append("g")
        .attr("transform", `translate(0,${legendHeight})`)
        .call(axis);
}
