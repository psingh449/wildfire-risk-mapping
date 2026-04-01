
# Commit 17 UI Patch (Manual Step)

In main.js, inside tooltip.html, replace with:

tooltip.html(`
<b>Risk:</b> ${p.risk_score.toFixed(2)}<br/>
<b>Hazard:</b> ${p.hazard_score.toFixed(2)}<br/>
<b>Exposure:</b> ${p.exposure_score.toFixed(2)}<br/>
<b>Vulnerability:</b> ${p.vulnerability_score.toFixed(2)}<br/>
<b>Resilience:</b> ${p.resilience_score.toFixed(2)}<br/>
<hr/>
<b>Population:</b> ${Math.round(p.exposure_population)}<br/>
<b>Building Value:</b> $${Math.round(p.building_value_est).toLocaleString()}<br/>
<b>EAL:</b> $${Math.round(p.eal).toLocaleString()}<br/>
<hr/>
<b>DEBUG:</b><br/>
hazard_wildfire: ${p.hazard_wildfire?.toFixed(2)}<br/>
hazard_vegetation: ${p.hazard_vegetation?.toFixed(2)}<br/>
vuln_poverty: ${p.vuln_poverty?.toFixed(2)}<br/>
res_fire_station_dist: ${p.res_fire_station_dist?.toFixed(2)}
`)
