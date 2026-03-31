const svg = d3.select("svg");
const width = +svg.attr("width");
const height = +svg.attr("height");

const projection = d3.geoIdentity().reflectY(true);
const path = d3.geoPath().projection(projection);

let geoData;

d3.json("data/processed/blocks.geojson").then(data => {
    geoData = data;
    projection.fitSize([width, height], geoData);
    render("risk_score");
});

d3.select("#metric").on("change", function() {
    render(this.value);
});

function render(metric) {

    const color = d3.scaleSequential(d3.interpolateReds)
        .domain([0,1]);

    svg.selectAll("path")
        .data(geoData.features)
        .join("path")
        .attr("d", path)
        .attr("fill", d => color(d.properties[metric]))
        .attr("stroke", "#333")
        .on("mouseover", function(event, d) {
            const p = d.properties;
            const tooltip = `
                Risk: ${p.risk_score.toFixed(2)}<br/>
                Hazard: ${p.hazard_score.toFixed(2)}<br/>
                Exposure: ${p.exposure_score.toFixed(2)}
            `;

            d3.select("body")
              .append("div")
              .attr("class", "tooltip")
              .html(tooltip)
              .style("left", event.pageX + "px")
              .style("top", event.pageY + "px");
        })
        .on("mouseout", function() {
            d3.selectAll(".tooltip").remove();
        });
}
