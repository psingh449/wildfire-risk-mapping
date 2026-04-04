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

### 2.1 Jargon-Free Problem Statement

Current wildfire risk maps usually summarize conditions over very large areas such as counties. That makes it hard to answer a practical question: **which neighborhoods inside a county are actually in the most danger?** A county may appear to have moderate wildfire risk overall, while some of its neighborhoods may face much higher danger because they are closer to forests, have more burnable vegetation, contain more people and homes, or have weaker access to transportation and emergency response services.

The problem addressed in this project is therefore to build a system that can identify wildfire risk at a much finer scale than county averages. Specifically, the goal is to estimate wildfire risk for each **census block**, compare those block-level results with county-level summaries, and determine whether county averages hide local wildfire hotspots. The system must combine physical wildfire conditions with information about who and what is exposed, which communities are more socially vulnerable, and how well communities can respond and recover.

### 2.2 Formal Problem Definition

Let `B = {b1, b2, ..., bn}` be the set of census blocks in the study region. For each block `b ∈ B`, the pipeline computes a set of normalized component scores derived from public environmental, demographic, and infrastructure datasets:

- hazard score `H(b) ∈ [0,1]`
- exposure score `E(b) ∈ [0,1]`
- vulnerability score `V(b) ∈ [0,1]`
- resilience score `R(b) ∈ [0,1]`

Each component score is built from lower-level features defined in `calculations.csv` and implemented in the project pipeline:

- `H(b)` from wildfire probability, vegetation/fuel proxy, and distance to forest
- `E(b)` from population, housing units, and estimated building value
- `V(b)` from poverty, elderly population share, and vehicle access proxy
- `R(b)` from distance to fire stations, distance to hospitals, and road access

The implemented wildfire risk model is:

**Risk(b) = H(b) × E(b) × V(b) × (1 − R(b))**

where `R(b)` is defined so that larger values indicate stronger resilience. This implemented form is consistent with the project’s bounded `0–1` scoring scheme in `calculations.csv`; it behaves like a resilience-adjusted risk model in which stronger response and recovery capacity reduces final risk.

The project also computes expected annual loss:

**EAL(b) = Risk(b) × BuildingValue(b)**

where `BuildingValue(b)` is approximated from housing units and ACS median property value at the block-group level.

Let `C = {c1, c2, ..., cm}` be the set of counties intersecting the study region. For each county `c`, block-level outputs are aggregated to county-scale validation measures such as:

- `CountyRisk(c) = mean(Risk(b))` for blocks within `c`
- `CountyEAL(c) = sum(EAL(b))` for blocks within `c`

The computational problem is to design and evaluate a reproducible mapping `f : B → [0,1]` such that:

1. `f(b)` identifies meaningful block-level variation in wildfire risk;
2. aggregated block outputs are comparable to external county-level reference systems such as FEMA NRI;
3. high-risk blocks align better with historical fire outcomes than coarse county averages alone; and
4. the results can be visualized interactively for exploration and interpretation.

### 2.3 Research Questions

This project is organized around the following questions:

1. **How much wildfire risk variation exists within counties when measured at census block resolution?**
2. **Do county-scale averages hide high-risk neighborhoods that become visible at block scale?**
3. **Can a block-level framework that combines hazard, exposure, vulnerability, and resilience produce plausible risk patterns when compared with FEMA NRI and historical fire data?**
4. **Can the outputs be packaged into a reproducible pipeline and interactive visual tool useful for analysis and decision support?**

### 2.4 System Flow Diagram

```mermaid
flowchart LR
    A[Public Datasets] --> B[Block Geometry + Joins]
    B --> C[Feature Engineering]
    C --> D[Hazard Score]
    C --> E[Exposure Score]
    C --> F[Vulnerability Score]
    C --> G[Resilience Score]
    D --> H[Risk Score]
    E --> H
    F --> H
    G --> H
    H --> I[Expected Annual Loss]
    H --> J[County Aggregation]
    I --> J
    J --> K[Validation Metrics]
    H --> L[Interactive GeoJSON Visualization]
    I --> L
    K --> L
```

**Figure Placeholder 1.** County-level wildfire choropleth versus block-level hotspot map, showing how a moderate county average can hide highly exposed neighborhoods. Insert final visualization screenshot here.

### 2.5 Input-Output Specification

| Element | Definition | Spatial Unit | Output Type |
| --- | --- | --- | --- |
| Input geometry | Census blocks or project block geometries | Block | GeoDataFrame |
| Hazard inputs | WHP, NLCD, forest distance | Block or raster-to-block | Numeric features |
| Exposure inputs | Population, housing, building value estimate | Block / block-group joined to block | Numeric features |
| Vulnerability inputs | Poverty, elderly, vehicle access | Block-group allocated to block | Numeric features |
| Resilience inputs | Fire stations, hospitals, road access | Block | Numeric features |
| Primary output | `risk_score` | Block | Float in `[0,1]` |
| Economic output | `eal`, `eal_norm` | Block | Float |
| Validation outputs | county aggregates, FEMA comparison, fire overlap, AUC, Gini | County / global / attached to blocks | Metrics + diagnostics |
| Visualization output | GeoJSON fields consumed by frontend | Block | Interactive map layer |

### 2.6 Variables Used in the Implemented Model

Table 1 summarizes the core variables from `calculations.csv` used directly in the implemented pipeline.

| Component | Implemented Variable | Description | Source |
| --- | --- | --- | --- |
| Hazard | `hazard_wildfire` | Mean wildfire hazard potential in block | USFS WHP |
| Hazard | `hazard_vegetation` | Fuel-density proxy from land cover | NLCD |
| Hazard | `hazard_forest_distance` | Inverted distance to forest | NLCD / derived |
| Exposure | `exposure_population` | Population count | Census PL |
| Exposure | `exposure_housing` | Housing unit count | Census H1 |
| Exposure | `exposure_building_value` | Housing units × median property value | ACS / derived |
| Vulnerability | `vuln_poverty` | Poverty proxy allocated to blocks | ACS |
| Vulnerability | `vuln_elderly` | Elderly share allocated to blocks | ACS |
| Vulnerability | `vuln_vehicle_access` | Vehicle-access proxy | ACS |
| Resilience | `res_fire_station_dist` | Access to fire stations | HIFLD / derived |
| Resilience | `res_hospital_dist` | Access to hospitals | HIFLD / derived |
| Resilience | `res_road_access` | Road connectivity proxy | OSM / derived |
| Model | `risk_score` | Composite wildfire risk | Derived |
| Model | `eal` | Expected annual loss estimate | Derived |

### 2.7 Why This Problem Is Non-Trivial

This is not a simple mapping task. The system requires combining multiple heterogeneous public datasets with different geographic units, formats, and semantics. Some features are raster-based, some come from APIs, some require nearest-neighbor spatial computation, and some are only available at coarser levels such as census block groups and must therefore be allocated downward to blocks. The project also requires normalization, provenance tracking, diagnostics, fallback logic for missing data, validation metrics, and an interactive frontend that exposes the results. Together, these steps satisfy the course requirement for large public data, non-trivial computation, and interactive visualization.

---

## 3. Literature Survey

The literature motivating this project spans wildfire science, disaster risk modeling, social vulnerability, and natural-hazard loss estimation. Existing work provides strong foundations for the project’s four main components, but the review also shows a consistent gap: the lack of a reproducible, publicly documented **block-level wildfire risk framework** that integrates hazard, exposure, vulnerability, and resilience while also comparing block outputs against county-scale systems.

### 3.1 Wildfire Hazard and Landscape Context

Moritz et al. (2014) argue that societies must learn to coexist with wildfire rather than treat it only as a controllable disturbance. Their central contribution is conceptual: wildfire emerges from interaction among climate, fuels, human settlement patterns, and governance. This paper is useful because it frames wildfire as a coupled human-natural systems problem rather than a purely biophysical hazard. That framing directly supports our decision to move beyond hazard-only mapping and include exposure, vulnerability, and resilience. Its limitation, however, is that it does not provide an operational fine-scale computational framework for neighborhood-level risk estimation.

Abatzoglou and Williams (2016) quantify the climatic drivers behind increased wildfire activity in western U.S. forests. Their work is valuable because it establishes that wildfire hazard is strongly associated with large-scale environmental conditions and that future wildfire risk is likely to intensify under climate change. For this project, the paper strengthens the motivation for hazard inputs such as wildfire hazard potential and vegetation-based fuel proxies. Its limitation is that it focuses on climatic explanation at broad regional scales rather than localized community risk or spatially explicit social consequences.

The project also draws practical inspiration from wildfire hazard products such as the U.S. Forest Service Wildfire Hazard Potential surface, which operationalizes broad wildfire likelihood into a spatial product usable for block-level zonal summaries. These hazard products are strong inputs, but by themselves they are insufficient for community risk because they do not measure the people, assets, or capacities that determine consequence.

### 3.2 Social Vulnerability and Unequal Consequences

Cutter, Boruff, and Shirley (2003) provide one of the foundational social-vulnerability frameworks for environmental hazards in the United States. Their contribution is to show that hazard impacts depend not only on physical exposure but also on socioeconomic characteristics such as poverty, age, housing quality, and mobility constraints. This study is highly useful for our project because it justifies including vulnerability variables alongside wildfire hazard. In particular, our block-level measures for poverty, elderly population, and vehicle access closely reflect the kinds of social factors emphasized in the vulnerability literature. A limitation is that Cutter et al. is not wildfire-specific and does not itself define a wildfire risk model.

Yarveysi et al. (2023) are especially relevant because they show that block-level analysis can reveal disproportionate natural-hazard burdens hidden by coarser spatial aggregation. Their work provides strong evidence that social vulnerability can vary sharply within counties and that fine spatial resolution matters for equity-sensitive risk assessment. This is directly aligned with the central argument of our project: county-level reporting can mask neighborhood-scale differences. The limitation, from our perspective, is that the study focuses primarily on vulnerability rather than a full wildfire risk model integrating hazard, exposure, and resilience.

Together, these studies support the project’s premise that wildfire consequences are socially uneven and that fine-scale geography matters. They also suggest that any credible wildfire risk map should include variables that capture differential evacuation difficulty and recovery capacity, not just fire likelihood.

### 3.3 Risk Frameworks and Economic Loss

The FEMA National Risk Index is the most directly relevant national risk framework for this project because it combines hazard, exposure, vulnerability, and community resilience into a unified public risk product. It demonstrates that multi-factor hazard risk systems are feasible at national scale and provides an external benchmark for validation. This project is intentionally compatible with that general structure, but differs in a major way: public NRI outputs are primarily communicated at county or tract scale, whereas our framework pushes the computation and visualization down to census blocks. The NRI is therefore useful both as a methodological reference and as a validation target. Its key limitation for our research question is its spatial coarseness for neighborhood hotspot detection.

Kreibich et al. (2014) emphasize the importance of more rigorous natural-hazard loss estimation and the distinction between hazard occurrence and realized damage. Their discussion is relevant because our project computes an economic consequence measure, expected annual loss (`eal`), by combining risk with estimated building value. This paper supports the argument that loss-based views of disaster impacts are necessary for practical planning and resource allocation. Its limitation is that it is not a block-level wildfire framework and does not address the geospatial allocation issues involved in moving from broad hazard concepts to neighborhood-scale estimates.

### 3.4 Where Existing Work Falls Short

The literature reveals an important pattern.

1. Wildfire science papers explain **where fires are likely** and why hazard is increasing.
2. Vulnerability research explains **which people are likely to suffer more**.
3. National risk systems demonstrate how to combine multiple components at broad scale.
4. But no single source in our reviewed set provides a reproducible, public, **block-level wildfire risk implementation** that integrates all four dimensions and directly tests whether county averages hide local hotspots.

That gap is the main motivation for this project.

### 3.5 Literature Comparison Table

Table 2 positions the proposed study against the most relevant prior work.

| Study | Main Idea | Useful for This Project | Key Limitation Relative to This Work |
| --- | --- | --- | --- |
| Moritz et al. (2014) | Wildfire is a coupled human-natural systems problem | Motivates integrating environmental and community factors | Conceptual and broad-scale; no block-level computational model |
| Abatzoglou & Williams (2016) | Climate change has increased wildfire conditions in western U.S. forests | Supports hazard motivation and environmental component design | Hazard-focused; no exposure, vulnerability, or resilience model |
| Cutter et al. (2003) | Social vulnerability shapes hazard consequences | Justifies poverty, age, and mobility variables | Not wildfire-specific and not a complete risk framework |
| Yarveysi et al. (2023) | Block-level vulnerability reveals hidden unequal risk | Strong evidence that fine spatial resolution matters | Focuses on vulnerability, not integrated wildfire risk |
| FEMA National Risk Index | National risk framework combining multiple dimensions | Reference architecture and county-level validation target | Public outputs too coarse to reveal block-scale wildfire hotspots |
| Kreibich et al. (2014) | Hazard studies should better account for economic loss | Motivates `eal` as an applied outcome measure | Not a wildfire-specific, neighborhood-scale mapping framework |

### 3.6 Implications for the Proposed Approach

The literature directly shaped the design of the implemented pipeline.

- From wildfire science, we adopt the view that hazard is necessary but not sufficient.
- From social vulnerability research, we incorporate demographic and socioeconomic disadvantage as a core part of risk.
- From national risk systems, we adopt a structured decomposition into hazard, exposure, vulnerability, and resilience.
- From hazard-loss research, we include an economic loss estimate rather than only a bounded risk score.
- From fine-scale vulnerability studies, we treat spatial resolution itself as a substantive research choice rather than a mere implementation detail.

In short, the literature suggests that the proposed method should outperform county-only interpretations not necessarily because county models are wrong, but because they are too spatially aggregated to reveal neighborhood concentration of wildfire danger.

### 3.7 Visual Placement of the Literature Gap

```mermaid
flowchart TD
    A[Wildfire Hazard Studies] --> D[Proposed Study]
    B[Social Vulnerability Studies] --> D
    C[County-Scale National Risk Frameworks] --> D
    E[Loss Estimation Literature] --> D
    D --> F[Block-Level Risk + County Comparison + Interactive Map]
```

**Figure Placeholder 2.** Literature positioning diagram or concept graphic showing how the project bridges hazard science, social vulnerability, resilience, and national risk frameworks. Insert final figure or poster-quality diagram here.

### 3.8 Summary of the Literature Gap

The strongest conclusion from the literature is that **the ingredients for a neighborhood-scale wildfire risk framework already exist in separate strands of prior work, but they have not been combined in a single reproducible block-level implementation for this problem**. That is the niche filled by this project. The contribution is not only a new visualization, nor only a new hazard layer, but a full analytical pipeline that integrates multiple public datasets, computes block-level wildfire risk and loss metrics, validates them against county-scale references, and exposes the results in an interactive spatial interface.

---

## 4. Proposed Method

*To be completed.*

## 5. Evaluation

*To be completed.*

## 6. Conclusions and Discussion

*To be completed.*
