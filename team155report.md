# TEAM-155: Wildfire Risk Mapping in the United States

**Team Members:** Phoenix Gray, Andrei Arion, Thomas Link, Celine Phan, Daisy Than, Pradeep Singh

---

## 1. Introduction

Wildfire risk in the United States is increasing because of the interaction between climate conditions, vegetation patterns, expanding development near wildland areas, and unequal community capacity to prepare for and recover from disasters. Although national risk products such as FEMA's National Risk Index provide useful large-scale assessments, they are primarily reported at coarse geographic resolutions such as counties. County-level summaries are helpful for broad comparison, but they often hide strong variation within counties, especially in places where forested land, road connectivity, housing patterns, and socioeconomic conditions change sharply over short distances.

This project addresses that limitation by building a neighborhood-scale wildfire risk mapping framework at **census block resolution**. Census blocks are the smallest geographic units defined by the U.S. Census Bureau, making them a suitable unit for revealing local hotspots that county averages may obscure. Two nearby blocks can face very different wildfire conditions because of differences in burnable vegetation, distance to forest edges, density of people and homes, poverty levels, age structure, vehicle access, and proximity to emergency services. A block-level system therefore provides a more actionable view of where wildfire danger is concentrated and where communities may face the greatest consequences if a fire occurs.

Our framework follows a standard disaster-risk perspective in which wildfire risk depends on four major components: **hazard, exposure, vulnerability, and resilience**. Hazard represents the likelihood or intensity of wildfire-related threat. Exposure captures the people, housing, and economic assets that could be affected. Vulnerability represents social conditions that can make evacuation, response, and recovery more difficult. Resilience represents the capacity of a community to respond and recover, including access to roads, hospitals, and fire stations. Rather than studying wildfire hazard alone, this approach models wildfire risk as a combination of physical threat and human consequence.

The project is designed as a reproducible data pipeline built from public datasets and transparent calculations. As documented in `calculations.csv`, the system computes wildfire-related features from sources including the U.S. Forest Service Wildfire Hazard Potential data, National Land Cover Database land-cover data, Census population and housing counts, ACS socioeconomic variables, HIFLD critical infrastructure layers, and OpenStreetMap road networks. These inputs are processed into standardized block-level indicators and combined into interpretable composite scores for hazard, exposure, vulnerability, resilience, overall risk, and expected annual loss. The resulting outputs are validated, exported to GeoJSON, and visualized in an interactive frontend so users can inspect risk patterns spatially.

This work is important for several audiences. Local governments and emergency planners need fine-grained maps to support evacuation planning, fuel treatment prioritization, and fire-response investment. Residents and homeowners benefit from understanding how wildfire risk differs across neighborhoods, even within the same county. Researchers and policymakers benefit from a framework that tests whether county-scale averages systematically mask concentrated neighborhood risk. More broadly, the project aligns with the course objective of integrating substantial public data, non-trivial computation, and an interactive visual interface into a complete analytical system.

The central premise of this report is that **county wildfire risk estimates can conceal important neighborhood-scale variation**. By producing a block-level wildfire risk map and comparing aggregated block results with county-scale benchmarks, this project aims to show that meaningful wildfire hotspots exist within counties and that these hotspots can be identified using a reproducible national framework.

---

## 2. Problem Definition

*To be completed.*

## 3. Literature Survey

*To be completed.*

## 4. Proposed Method

*To be completed.*

## 5. Evaluation

*To be completed.*

## 6. Conclusions and Discussion

*To be completed.*
