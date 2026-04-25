# TEAM-155: Wildfire Risk Mapping in the United States

**Team Members:** Phoenix Gray, Andrei Arion, Thomas Link, Celine Phan, Daisy Than, Pradeep Singh

**Reproducibility (code vs. text):** The pipeline in the repository maps wildfire risk to U.S. Census **block group** polygons (see project **README** and `calculations.csv`). A few sections below use “census block” in the *informal* sense of a small area; the exported GeoJSON and all joins use **block group** `GEOID` as implemented.

---

## 1. Introduction

Wildfire risk in the United States is increasing because of the interaction between climate conditions, vegetation patterns, expanding development near wildland areas, and unequal community capacity to prepare for and recover from disasters. Although national risk products such as FEMA's National Risk Index provide useful large-scale assessments, they are primarily reported at coarse geographic resolutions such as counties. County-level summaries are helpful for broad comparison, but they often hide strong variation within counties, especially in places where forested land, road connectivity, housing patterns, and socioeconomic conditions change sharply over short distances.

This project addresses that limitation by building a neighborhood-scale wildfire risk mapping framework at **Census block group resolution** (as implemented in the repository’s GeoJSON and pipeline). Block groups are small statistical areas—larger than individual census blocks but still fine enough to reveal local hotspots that county averages may obscure. Two nearby small areas can face very different wildfire conditions because of differences in burnable vegetation, distance to forest edges, density of people and homes, poverty levels, age structure, vehicle access, and proximity to emergency services. A neighborhood-level system therefore provides a more actionable view of where wildfire danger is concentrated and where communities may face the greatest consequences if a fire occurs.

Our framework follows a standard disaster-risk perspective in which wildfire risk depends on four major components: **hazard, exposure, vulnerability, and resilience**. Hazard represents the likelihood or intensity of wildfire-related threat. Exposure captures the people, housing, and economic assets that could be affected. Vulnerability represents social conditions that can make evacuation, response, and recovery more difficult. Resilience represents the capacity of a community to respond and recover, including access to roads, hospitals, and fire stations. Rather than studying wildfire hazard alone, this approach models wildfire risk as a combination of physical threat and human consequence.

The project is designed as a reproducible data pipeline built from public datasets and transparent calculations. As documented in `calculations.csv`, the system computes wildfire-related features from sources including the U.S. Forest Service Wildfire Hazard Potential data, National Land Cover Database land-cover data, Census population and housing counts, ACS socioeconomic variables, HIFLD critical infrastructure layers, and OpenStreetMap road networks. These inputs are processed into standardized block-group-level indicators and combined into interpretable composite scores for hazard, exposure, vulnerability, resilience, overall risk, and expected annual loss. The canonical schema in `calculations.csv` now also stores composite-weight metadata through `weight_group` and `weight` columns, so both feature definitions and default weighting rules are documented in one place. The resulting outputs are validated, exported to GeoJSON, and visualized in an interactive frontend so users can inspect risk patterns spatially.

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

### 2.5 Why County Averaging Hides Wildfire Risk

A central problem in coarse disaster reporting is that averaging can combine very low-risk and very high-risk neighborhoods into one moderate county value. In wildfire contexts this can happen when sparsely populated forest edges, denser residential areas, and communities with different evacuation capacity are all summarized together. The result is that blocks facing much higher danger than the county mean may not stand out in county-scale products.

**Figure Placeholder 1A.** Illustration of county averaging effect, adapted from the project’s earlier proposal material. Replace with final figure showing how a county average such as `0.39` can conceal higher-risk neighborhood values.

### 2.6 Input-Output Specification

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

### 2.7 Variables Used in the Implemented Model

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
| Vulnerability | `vuln_uninsured` | Uninsured share proxy | ACS (B27010) |
| Resilience | `res_vehicle_access` | Vehicle access proxy | ACS (B08201) |
| Resilience | `res_median_household_income` | Income capacity proxy | ACS (B19013) |
| Resilience | `res_internet_access` | Connectivity proxy | ACS (B28002) |
| Model | `risk_score` | Composite wildfire risk | Derived |
| Model | `eal` | Expected annual loss estimate | Derived |

### 2.8 Why This Problem Is Non-Trivial

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

### 4.1 Intuition

The intuition behind the proposed method is simple: a place should be considered high wildfire risk only when several conditions occur together. A block should score high if wildfire hazard is high, if many people or valuable structures are exposed, if social conditions make response and recovery harder, and if local resilience is weak. A hazard-only model misses human consequence; a vulnerability-only model misses the actual fire environment; and a county-average model smooths away meaningful local differences. By computing all of these components at block scale, the method should reveal clusters of concentrated wildfire danger that are invisible in county summaries.

This structure is also expected to outperform coarse risk interpretations in a practical sense. Two blocks may lie in the same county and share the same county wildfire label, yet differ sharply in forest proximity, housing density, poverty, vehicle ownership, and emergency access. Our approach preserves those local contrasts. The expected benefit is therefore not that the model invents new wildfire physics, but that it combines known environmental and social signals at a more decision-relevant spatial scale.

### 4.2 Overall Pipeline Architecture

The implemented method is a modular pipeline that ingests public datasets, derives standardized block-level features, computes composite scores, validates the results, and exports them for visualization. The pipeline uses `calculations.csv` as the canonical feature contract, meaning each implemented metric is associated with a data source, transformation rule, validation range, output field. In the current schema, weighted composite inputs also carry `weight_group` and `weight` metadata so that default component weights are documented centrally and can be read directly by the feature-building code.

```mermaid
flowchart LR
    A[Raw Public Data] --> B[Ingestion]
    B --> C[Preprocessing]
    C --> D[Feature Engineering]
    D --> E[Composite Scores]
    E --> F[Risk and EAL]
    F --> G[Validation Metrics]
    G --> H[GeoJSON Export]
    H --> I[Interactive Frontend]
```

**Figure Placeholder 3.** End-to-end pipeline diagram using actual file names and modules from the implementation. Insert a refined exported diagram here.

### 4.3 Data Sources and Spatial Integration

The pipeline combines several public datasets with different spatial formats:

| Data Source | Example Variables Used | Native Format | Role in Method |
| --- | --- | --- | --- |
| USFS Wildfire Hazard Potential | `hazard_wildfire` | Raster | Hazard likelihood proxy |
| NLCD | `hazard_vegetation`, forest-distance inputs | Raster / derived polygons | Fuel and forest proximity |
| Census PL / H1 | population, housing | API / tabular | Exposure |
| ACS 5-year | property value, poverty, age, vehicle access | API / tabular | Exposure + vulnerability |
| HIFLD | fire stations, hospitals | Point layers | Resilience |
| OpenStreetMap / Overpass | road network | Vector line data | Resilience |
| FEMA NRI | county-scale reference metrics | Tabular | Validation |
| MTBS fire perimeters | burned-area history | Polygon layer | Validation |

Because these datasets are not aligned to the same geography, the method performs several joins and transformations:

1. raster-to-block zonal statistics for wildfire and vegetation features;
2. nearest-neighbor distance calculations from block centroids to infrastructure or forest features;
3. joins from block-group ACS data down to blocks using geographic keys and population-based allocation;
4. area- or density-based transformations for road access and land-cover proxies; and
5. final export of all derived block-level outputs to a single GeoJSON layer.

### 4.4 Feature Engineering by Component

#### 4.4.1 Hazard

The hazard component captures the underlying wildfire threat from vegetation and landscape conditions.

- **Wildfire Hazard Potential (`hazard_wildfire`)** is computed as the mean WHP value of raster pixels intersecting each block.
- **Vegetation/Fuel Proxy (`hazard_vegetation`)** is derived from NLCD by classifying relevant fuel-supporting land-cover classes such as forest or shrub and measuring their share within the block.
- **Forest Proximity (`hazard_forest_distance`)** is computed as an inverted nearest distance from block centroid to forest features, using the form `1 / (1 + distance_km)`.

These features are normalized to `[0,1]` and combined using configurable weights documented in `calculations.csv`:

**HazardScore = w1·hazard_wildfire + w2·hazard_vegetation + w3·hazard_forest_distance**

This construction is intended to capture both direct wildfire likelihood and a wildland-urban interface effect.

#### 4.4.2 Exposure

The exposure component measures how much population, housing, and economic value are located in each block.

- **Population (`exposure_population`)** comes from Census PL block counts.
- **Housing Units (`exposure_housing`)** come from Census H1.
- **Building Value (`exposure_building_value`)** is approximated as housing units multiplied by ACS block-group median property value, joined to blocks.

The exposure component is then formed as a normalized combination:

**ExposureScore = norm(population) + norm(housing) + norm(building_value)**

or, in implementation terms, a weighted normalized sum with bounded output. This allows the model to capture both human and economic consequence.

#### 4.4.3 Vulnerability

The vulnerability component captures social conditions that may worsen wildfire consequence even when physical exposure is similar.

- **Poverty (`vuln_poverty`)** is derived from ACS poverty counts/rates at block-group scale and allocated to blocks using population-based weighting.
- **Elderly Population (`vuln_elderly`)** is derived similarly from ACS age tables.
- **Uninsured Share (`vuln_uninsured`)** uses ACS health insurance coverage statistics as a vulnerability proxy.

The implementation combines normalized vulnerability features through a weighted sum:

**VulnerabilityScore = w1·vuln_poverty + w2·vuln_elderly + w3·vuln_uninsured**

This structure is motivated by the literature showing that age, poverty, and transportation constraints strongly affect disaster response and recovery.

#### 4.4.4 Resilience

The resilience component measures community access to emergency services and evacuation-supporting infrastructure.

- **Vehicle Access (`res_vehicle_access`)** uses ACS vehicle-availability statistics as an evacuation capacity proxy.
- **Median household income (`res_median_household_income`)** uses ACS income as a capacity proxy.
- **Internet access (`res_internet_access`)** uses ACS internet access as a connectivity / information proxy.

These features are combined by weighted normalized sum:

**ResilienceScore = w1·res_vehicle_access + w2·res_median_household_income + w3·res_internet_access**

Higher resilience values lower final risk in the implemented model.

### 4.5 Unified Risk and Economic Model

Once the four component scores are computed, the pipeline calculates the main outputs.

#### 4.5.1 Risk Score

The core implemented equation is:

**risk_score = hazard_score × exposure_score × vulnerability_score × (1 − resilience_score)**

This formulation preserves four desirable properties:

1. risk remains bounded in `[0,1]`;
2. risk increases when any of hazard, exposure, or vulnerability increases;
3. risk decreases when resilience increases; and
4. a block with very low value in one essential component cannot dominate the system unfairly through addition alone.

The multiplicative form therefore acts as a conservative interaction model: high risk emerges when several risk-driving conditions are simultaneously elevated.

#### 4.5.2 Expected Annual Loss

To make the result more interpretable for planning, the model computes expected annual loss:

**eal = risk_score × exposure_building_value**

and then a normalized version for mapping:

**eal_norm = (eal − min(eal)) / (max(eal) − min(eal))**

This gives the system both a bounded comparative risk score and a dollar-denominated consequence estimate.

### 4.6 Provenance, Diagnostics, and Fallback Logic

A practical challenge in public-data pipelines is incomplete or missing input layers. The implementation addresses this through provenance and diagnostics columns documented in `README.md`.

- Each field may be accompanied by `_source` and `_provenance` metadata.
- Each record includes a `diagnostics` field summarizing validation issues.
- When certain optional external datasets are missing, the pipeline computes safe fallback values rather than failing completely.
- Validation rules from `calculations.csv` enforce bounds, nullability, and type expectations.

This design makes the method more robust for course demonstration and future extension. It also improves interpretability by distinguishing between real-data and fallback-data outputs.

### 4.7 Validation-Oriented Outputs

Although full evaluation is described in Section 5, the proposed method explicitly produces validation-ready outputs as part of the pipeline.

| Validation Output | Purpose |
| --- | --- |
| `block_to_county_mapping` | Aggregation from blocks to counties |
| `county_risk` | Compare aggregated block risk with county references |
| `county_eal` | Aggregate loss for county-scale comparison |
| `fema_nri_comparison` | External benchmark against FEMA NRI |
| `fire_overlap_ratio` | Historical burned-area overlap test |
| `auc_score` | Predictive discrimination of high-risk blocks |
| `risk_concentration` | Share of risk in top blocks |
| `gini_risk` | Spatial inequality of risk distribution |

This is important because the method is not only a score generator; it is built to support structured assessment of whether block-level outputs are plausible and useful.

### 4.8 Interactive Visualization Design

The frontend is a required part of the project method, not just a presentation layer. The output GeoJSON is visualized in an interactive map interface so users can inspect patterns that static county averages would hide.

The intended interface supports:

- map-based exploration of block-level `risk_score`, `eal_norm`, and component scores;
- field-driven coloring by hazard, exposure, vulnerability, resilience, risk, or loss;
- hover or click details for each block, including diagnostics and provenance;
- comparison of neighboring blocks within the same county; and
- interpretation of validation-related fields when available.

```mermaid
flowchart TD
    A[GeoJSON with Block Features] --> B[Frontend Loader]
    B --> C[Choropleth Rendering]
    B --> D[Tooltip / Details Panel]
    B --> E[Layer Selector]
    B --> F[Diagnostics View]
```

**Figure Placeholder 4.** Main interactive map interface showing wildfire risk by block with tooltip details. Insert screenshot from final visualization here.

**Figure Placeholder 5.** Alternate layer view, e.g. vulnerability or resilience, demonstrating how the interface supports component-level inspection. Insert screenshot here.

Table 3 documents the recommended visualization palette for distinct layer identification.

| Layer | Color Name | Hex | Intended Meaning |
| --- | --- | --- | --- |
| Risk | Crimson red | `#D73027` | Primary danger layer |
| Hazard | Burnt orange | `#F46D43` | Fire and ignition potential |
| Exposure | Golden orange | `#FDAE61` | Population and asset presence |
| Vulnerability | Purple | `#8073AC` | Social sensitivity and fragility |
| Resilience | Teal green | `#1A9850` | Response and recovery capacity |
| Expected Annual Loss (`EAL`) | Deep blue | `#4575B4` | Economic consequence |
| Diagnostics / Missing | Neutral gray | `#9E9E9E` | Missing, fallback, or warning state |

This palette keeps `risk` visually strongest, separates `hazard` from `risk`, and assigns `resilience` a positive green hue because stronger resilience lowers final risk.

### 4.9 Why the Method Should Be Better Than the State of the Art for This Use Case

The method is expected to improve on county-level wildfire interpretation for three reasons.

1. **Higher spatial resolution.** Block-level outputs preserve local variation in fuels, population, vulnerability, and emergency access.
2. **Integrated structure.** The model captures both wildfire likelihood and human consequence, rather than reducing the problem to hazard alone.
3. **Operational reproducibility.** Every major variable is defined in `calculations.csv`, implemented in code, validated, and exported to a user-facing interface.

In other words, the novelty is not one single algorithmic trick. It is the combination of fine spatial resolution, multi-source feature integration, resilience-aware risk modeling, and direct visual comparison of neighborhood hotspots against coarse administrative summaries.

### 4.10 Implementation Summary Table

| Stage | Main Operation | Example Functions / Outputs |
| --- | --- | --- |
| Ingestion | Load raw tabular and geospatial inputs | Census, ACS, NLCD, HIFLD, OSM, FEMA, MTBS |
| Preprocessing | Clean schemas, harmonize keys, prepare geometry | block IDs, county joins, centroids |
| Feature engineering | Compute direct and derived variables | `compute_hazard_*`, `compute_exposure_*`, `compute_vuln_*`, `compute_res_*` |
| Modeling | Build component scores and final outputs | `hazard_score`, `exposure_score`, `vulnerability_score`, `resilience_score`, `risk_score`, `eal` |
| Validation | Aggregate and compare with external references | county metrics, FEMA comparison, overlap, AUC, Gini |
| Export | Write processed block GeoJSON | `data/processed/blocks.geojson` |
| Visualization | Render interactive map and panels | frontend fields from GeoJSON |

### 4.11 Method Limitations by Design

The method also makes several practical approximations.

- Some socioeconomic variables are only available at block-group scale and must be allocated to blocks.
- Building value is estimated from housing counts and median property value rather than parcel-level appraisal data.
- Road access is measured through a simple network-density proxy rather than full evacuation simulation.
- Resilience is represented through infrastructure access, not a full institutional-capacity model.

These are limitations, but they are deliberate tradeoffs that preserve national reproducibility using public data.

---

## 5. Evaluation

### 5.1 Evaluation Goals

The evaluation is designed to answer two broad questions. First, does the block-level wildfire framework produce internally consistent and externally plausible results? Second, does the block-level approach reveal spatial patterns that would be hidden by county-scale summaries alone?

To address these questions, the evaluation uses the validation outputs already implemented in the pipeline and described in `calculations.csv`. Rather than relying on a single benchmark, the project uses multiple complementary tests: county aggregation checks, comparison with FEMA NRI, historical fire overlap, discrimination-based metrics, and concentration/inequality metrics. Together, these tests assess agreement with known reference systems, usefulness for identifying historically burned areas, and the degree to which wildfire risk is concentrated within counties.

### 5.2 Testbed

The computational testbed consists of the full wildfire risk pipeline described in Section 4, running on block-level geometries with joined environmental, demographic, and infrastructure features. The main output artifact is a processed GeoJSON containing block-level scores and diagnostics.

The evaluation uses the following categories of data:

| Category | Example Files / Sources | Purpose in Evaluation |
| --- | --- | --- |
| Block-level model outputs | `risk_score`, `eal`, `eal_norm`, component scores | Primary prediction outputs |
| County mapping | block-to-county aggregation | Convert block results to county metrics |
| External county benchmark | FEMA National Risk Index | Compare aggregated model behavior |
| Historical fire reference | MTBS fire perimeters | Test whether high-risk blocks overlap known fire activity |
| Derived labels | burned / not-burned or top-risk threshold labels | AUC and overlap experiments |
| UI exports | GeoJSON fields displayed in the frontend | Qualitative interpretation of spatial patterns |

Where external files are absent, the pipeline includes safe fallback logic so that execution remains possible. However, the strongest evaluation results are obtained when the FEMA NRI county table and MTBS fire perimeter data are present.

### 5.3 Example Study Area

Although the framework is designed to be extensible beyond a single county, **Butte County, California** is an especially useful example study area for demonstration and interpretation. It contains wildfire-prone Sierra foothill terrain, a mix of forest and residential land, and the legacy of the **2018 Camp Fire**, making it a strong candidate for illustrating within-county variation in hazard, exposure, and vulnerability. It is therefore a practical place to compare county wildfire summaries against neighborhood-scale block patterns.

### 5.4 Evaluation Questions

The evaluation section is organized around the following specific questions.

**EQ1.** Do aggregated block-level risk estimates behave similarly to established county-scale wildfire risk benchmarks?

**EQ2.** Do aggregated block-level economic loss estimates produce interpretable county-scale loss patterns?

**EQ3.** Are historically burned areas more likely to fall in blocks that our model ranks as high risk?

**EQ4.** Is wildfire risk concentrated in a relatively small share of blocks inside each county, supporting the claim that county averages hide hotspots?

**EQ5.** Does the interactive visualization make those within-county contrasts legible to a user?

### 5.5 Evaluation Metrics Implemented in the Pipeline

The implemented evaluation metrics are summarized below.

| Metric | Implemented Output | Interpretation |
| --- | --- | --- |
| County mean risk | `county_risk` | County-scale aggregate of block risk |
| County total EAL | `county_eal` | County-scale aggregate of economic consequence |
| FEMA comparison | `fema_nri_comparison` | Agreement with county benchmark, e.g. correlation / RMSE |
| Historical fire overlap | `fire_overlap_ratio` | Share of burned area captured in top-risk blocks |
| Predictive discrimination | `auc_score` | Ability of `risk_score` to separate burned vs non-burned labels |
| Risk concentration | `risk_concentration` | Share of total risk held by the top 10% of blocks |
| Gini inequality | `gini_risk` | Unevenness of block risk distribution |

These metrics are attached to the data pipeline because evaluation is treated as part of the analytical workflow rather than an afterthought.

### 5.6 Experiment 1: County Risk Comparison with FEMA NRI

#### Purpose

This experiment tests whether aggregated block-level results are broadly compatible with an established county-scale wildfire risk reference.

#### Method

1. Compute `risk_score` for all blocks.
2. Map each block to its county using the block-to-county mapping.
3. Aggregate block risk by county using the implemented county mean function.
4. Join the resulting county table to FEMA NRI wildfire risk values by county FIPS.
5. Compute summary comparison metrics such as correlation and RMSE.

#### Rationale

The purpose is not to reproduce FEMA exactly. Our model uses different spatial granularity and feature engineering choices. Instead, the goal is to check whether counties that score high in FEMA also tend to receive high aggregate scores in our framework.

#### Expected Observation

We expect moderate positive agreement with FEMA NRI at county scale, while still preserving substantially more local variation inside counties.

**Result Placeholder Table 3. County-Level Comparison with FEMA NRI**

| County FIPS / Summary | FEMA NRI Wildfire Risk | Aggregated `county_risk` | Absolute Error | Notes |
| --- | --- | --- | --- | --- |
| Placeholder County 1 | TBD | TBD | TBD | Replace with actual values |
| Placeholder County 2 | TBD | TBD | TBD | Replace with actual values |
| Overall Correlation | TBD | — | — | Insert Pearson/Spearman if computed |
| Overall RMSE | TBD | — | — | Insert RMSE if computed |

**Figure Placeholder 6.** Scatterplot of aggregated `county_risk` versus FEMA NRI wildfire risk by county. Insert final chart here.

### 5.7 Experiment 2: County Expected Annual Loss Aggregation

#### Purpose

This experiment evaluates whether block-level economic risk estimates aggregate into plausible county-scale loss patterns.

#### Method

1. Compute block-level `eal = risk_score × exposure_building_value`.
2. Sum `eal` within counties to produce `county_eal`.
3. Compare county totals across the study area.
4. When possible, qualitatively compare high-EAL counties with known wildfire-prone counties or external summaries.

#### Rationale

A county may have moderate mean risk but very high total expected annual loss if it contains many exposed structures. This experiment distinguishes concentrated physical danger from total economic consequence.

#### Expected Observation

We expect `county_eal` to emphasize heavily developed wildfire-prone counties more strongly than mean risk alone.

**Result Placeholder Table 4. County EAL Ranking**

| County | `county_eal` | `county_risk` | Interpretation |
| --- | --- | --- | --- |
| Placeholder County A | TBD | TBD | Replace with actual result |
| Placeholder County B | TBD | TBD | Replace with actual result |
| Placeholder County C | TBD | TBD | Replace with actual result |

**Figure Placeholder 7.** County-level map or ranked bar chart of `county_eal`. Insert final figure here.

### 5.8 Experiment 3: Historical Fire Validation

#### Purpose

This experiment tests whether blocks ranked as high risk overlap with real historical wildfire footprints.

#### Method

1. Load historical fire perimeters from MTBS.
2. Overlay fire perimeters with block geometries.
3. Label blocks as burned or not burned, or compute burned area share where appropriate.
4. Compare top-risk blocks against historical burn overlap.
5. Compute `fire_overlap_ratio`, defined in the pipeline as the share of burned area captured within high-risk blocks.

#### Rationale

A useful wildfire risk map should place historically burned areas disproportionately in the upper end of the risk distribution, even though it is not intended to predict exact ignition locations.

#### Expected Observation

We expect the highest-risk decile of blocks to capture a disproportionately large share of historically burned area relative to random or uniform selection.

**Result Placeholder Table 5. Historical Fire Overlap**

| Metric | Value | Interpretation |
| --- | --- | --- |
| Top-risk threshold used | TBD | e.g. top 10% of blocks |
| `fire_overlap_ratio` | TBD | Higher is better |
| Burned area in top-risk blocks | TBD | Insert computed share |
| Burned area outside top-risk blocks | TBD | Insert computed share |

**Figure Placeholder 8.** Overlay map showing historical fire perimeters on top of block-level `risk_score`. Insert screenshot here.

### 5.9 Experiment 4: AUC-Based Fire Prediction Test

#### Purpose

This experiment evaluates the ranking power of `risk_score` as a classifier-like signal for historical burn labels.

#### Method

1. Use historical fire overlap to derive binary block labels, such as burned vs not burned.
2. Use `risk_score` as the ranking variable.
3. Compute ROC AUC using the implemented `auc_score` function.

#### Rationale

This does not turn the project into a pure prediction model, but it provides a standard discrimination metric: if a randomly chosen burned block tends to have higher risk than a randomly chosen non-burned block, the AUC will exceed 0.5.

#### Expected Observation

We expect AUC to be meaningfully above random chance, with the exact value depending on coverage, region, and label quality.

**Result Placeholder Table 6. Predictive Discrimination**

| Metric | Value | Interpretation |
| --- | --- | --- |
| `auc_score` | TBD | > 0.5 indicates better-than-random ranking |
| Positive label definition | TBD | e.g. burned overlap > 0 |
| Sample size | TBD | Number of labeled blocks |

**Figure Placeholder 9.** ROC curve for historical fire prediction using block `risk_score`. Insert final figure here.

### 5.10 Experiment 5: Risk Concentration and Inequality

#### Purpose

This experiment directly tests the report’s core claim that county averages hide neighborhood hotspots.

#### Method

1. Sort blocks within a county or the whole study area by `risk_score`.
2. Compute `risk_concentration`, e.g. the share of total risk held by the top 10% of blocks.
3. Compute `gini_risk` using the Lorenz-curve implementation.
4. Compare the distribution to what would be expected under a more uniform spatial pattern.

#### Rationale

If risk is strongly concentrated, then county averages are intrinsically poor summaries of neighborhood danger because they mix high-risk and low-risk blocks into a single value.

#### Expected Observation

We expect a relatively high concentration of total risk in a small share of blocks, especially in counties that contain both developed settlement and nearby wildland or forest zones.

**Result Placeholder Table 7. Risk Concentration**

| Metric | Value | Interpretation |
| --- | --- | --- |
| `risk_concentration` | TBD | Share of total risk in top-decile blocks |
| `gini_risk` | TBD | Higher means more uneven distribution |
| County / study area | TBD | Specify evaluation scope |

**Figure Placeholder 10.** Lorenz curve of block-level `risk_score` and annotation of `gini_risk`. Insert final chart here.

### 5.11 Experiment 6: Qualitative Visual Evaluation of the Interface

#### Purpose

This experiment evaluates whether the interactive frontend makes block-level contrasts understandable to a user.

#### Method

1. Load the processed GeoJSON in the browser-based visualization.
2. Inspect counties with moderate aggregate risk but visibly heterogeneous block values.
3. Switch layers among hazard, exposure, vulnerability, resilience, `risk_score`, and `eal_norm`.
4. Use tooltips or details panels to inspect individual blocks and confirm that diagnostics, provenance, and derived fields are accessible.

#### Rationale

Because the course project requires an interactive visual interface, evaluation should also confirm that the system supports user interpretation rather than only numeric output generation.

#### Expected Observation

We expect the interface to make within-county variation visually obvious and to provide drill-down support for diagnosing why one block scores differently from another.

**Figure Placeholder 11.** Screenshot sequence showing one county at county scale, then zoomed block scale, then tooltip details panel. Insert final UI screenshots here.

### 5.12 Summary of Evaluation Logic

The evaluation framework intentionally uses several complementary perspectives.

- **Agreement tests** ask whether the model is plausible relative to known county benchmarks.
- **Historical overlap tests** ask whether high-risk areas align with real fire experience.
- **Ranking tests** ask whether the model distinguishes burned from non-burned blocks better than chance.
- **Concentration tests** ask whether risk is spatially clustered enough to justify block-level analysis.
- **Qualitative visualization tests** ask whether the interface makes the results interpretable.

A model could perform reasonably on one of these tests and poorly on another, so using all of them provides a more balanced assessment.

### 5.13 Anticipated Observations

Based on the design of the method and the implemented validation outputs, the main expected observations are:

1. aggregated block results should show positive but imperfect agreement with FEMA NRI;
2. high-risk blocks should overlap historical fire areas more than low-risk blocks do;
3. AUC should exceed random chance for historical burn labels;
4. a relatively small share of blocks should contain a large share of total risk; and
5. the frontend should visually confirm that county averages suppress meaningful local contrasts.

These expected results would support the main project claim that **block-level wildfire risk provides a more informative view of neighborhood danger than county averages alone**.

### 5.14 Threats to Validity

Several factors may affect evaluation quality.

- Historical fires are not perfect ground truth for future wildfire risk.
- FEMA NRI is a related but not identical target, so disagreement does not automatically imply model failure.
- Some variables are allocated from coarser geographies, which may blur fine-scale social patterns.
- External validation files may be incomplete, missing, or temporally mismatched with the study period.
- Safe fallback values keep the pipeline operational, but they reduce the strength of empirical validation when used.

These threats do not invalidate the framework, but they should be considered when interpreting final quantitative results.

### 5.15 Reproducibility of Evaluation

A strength of the project is that evaluation is reproducible through the same pipeline architecture used for model computation. Once the required external datasets are placed in the documented paths, the evaluation outputs are recomputed automatically and attached to the GeoDataFrame. This means the experiments are not one-off manual analyses; they are part of the end-to-end system.

---

## 6. Conclusions and Discussion

This project proposes and implements a reproducible wildfire risk mapping framework at **census block resolution**, with the goal of revealing neighborhood-scale wildfire hotspots that county-level averages can hide. The work combines four major components—hazard, exposure, vulnerability, and resilience—into a unified block-level risk score and an expected annual loss measure. It also packages the full workflow into a transparent pipeline with validation outputs, diagnostics, provenance tracking, and an interactive visualization layer.

The central contribution of the project is not only a finer-grained map, but a **multi-source analytical system** that connects public environmental, demographic, and infrastructure datasets into a single operational framework. In that sense, the project sits between three kinds of prior work: hazard-focused wildfire science, social-vulnerability research, and county-scale disaster risk systems such as FEMA NRI. By integrating ideas from each of these areas, the project demonstrates how wildfire danger can be studied as both a physical and a social phenomenon at neighborhood scale.

From a methodological perspective, the project shows that block-level wildfire assessment is feasible using public data and standard geospatial computation. The pipeline supports raster summarization, distance-based accessibility features, census joins, allocation of coarser ACS variables to blocks, composite score construction, aggregation back to county scale, and export to a web-ready GeoJSON product. This satisfies the course requirement for non-trivial computation on large real datasets while also producing a visual interface through which the results can be inspected.

The evaluation framework was designed to test the system from multiple angles rather than relying on a single benchmark. County aggregation metrics evaluate consistency with broader public risk systems, historical fire overlap and AUC metrics test whether high-risk blocks align with observed burn patterns, and concentration metrics test the project’s main claim that wildfire risk is unevenly distributed within counties. Even before final numeric values are inserted, the structure of the evaluation supports the hypothesis that **county averages are often too coarse to capture neighborhood concentration of wildfire risk**.

### 6.1 Main Takeaways

The most important takeaways of this work are the following:

1. **Wildfire risk is spatially heterogeneous at short distances.** Blocks within the same county can differ substantially in hazard, exposure, social vulnerability, and emergency access.
2. **County-scale reporting is useful but incomplete.** It provides broad regional summaries, but it is poorly suited for locating local hotspots or supporting neighborhood-level planning.
3. **A block-level framework can integrate physical and social dimensions of risk.** This allows wildfire assessment to move beyond hazard-only maps.
4. **Interactive visualization matters.** Spatial patterns that are difficult to understand in tables become immediately interpretable when block-level outputs are displayed on a map with component-level drill-down.

### 6.2 Practical Implications

The project has several applied implications.

- **Emergency planning:** local agencies can use block-level patterns to prioritize evacuation preparation, route planning, and response staging.
- **Mitigation investment:** wildfire fuel treatment or preparedness funding can be directed toward clusters of blocks where high hazard and high vulnerability coincide.
- **Public communication:** residents can better understand how their neighborhood differs from nearby areas, even within the same county.
- **Policy analysis:** block-level results offer a stronger basis for examining environmental inequality and the intersection of poverty with climate-related hazards.

These applications directly connect to the broader motivating question in the course materials: where do vulnerable communities live, and where are climate emergencies likely to cause the greatest harm?

### 6.3 Limitations

The project also has important limitations.

First, several socially meaningful variables are not natively available at block scale and must be inferred from block-group data. This introduces smoothing that may weaken the precision of neighborhood estimates. Second, the building-value model is an approximation based on housing counts and ACS median values rather than parcel-level appraisal data. Third, the resilience component is intentionally simple; it measures access to selected infrastructure rather than full institutional, financial, or governance capacity. Fourth, historical fire validation is useful but imperfect, because past fires are not a complete representation of future wildfire risk. Finally, the quality of external validation depends on the availability and temporal alignment of FEMA and MTBS reference data.

These limitations should make users cautious about treating the outputs as exact forecasts. The project is best understood as a **decision-support and spatial prioritization framework**, not as a deterministic wildfire prediction engine.

### 6.4 Future Work

Several extensions would strengthen the framework.

- replace block-group allocation proxies with finer-grained socioeconomic data where available;
- incorporate parcel-level or assessor-based building value estimates;
- model evacuation capacity using full road-network travel analysis rather than road-density proxies;
- incorporate additional wildfire-relevant variables such as slope, aspect, drought, wind exposure, defensible space, or structure age;
- evaluate the framework across more counties and compare regional behavior systematically; and
- improve the frontend with richer filtering, side-by-side county/block comparison, and embedded validation dashboards.

A longer-term research direction would be to examine whether the block-level framework can support publishable evidence about how county-scale risk systems may underrepresent concentrated neighborhood vulnerability.

### 6.5 Final Conclusion

Overall, this project demonstrates that a **block-level wildfire risk framework is both feasible and useful**. It extends existing county-scale interpretations by preserving local variation, integrates multiple dimensions of wildfire consequence, and provides a reproducible computational and visual workflow grounded in public data. The key insight is that wildfire risk is not evenly distributed within administrative units, and that this unevenness matters for planning, policy, and equity. If the final empirical results follow the expected patterns described in Section 5, then the project will support its main claim: **county averages can hide high-risk neighborhoods, and block-level analysis provides a more informative picture of wildfire danger in the United States.**

### 6.6 Team Effort Statement

All team members have contributed a similar amount of effort across the design, implementation, analysis, and reporting of this project.

---

## References

1. Moritz, M. A., et al. 2014. Learning to coexist with wildfire. *Nature*. https://www.nature.com/articles/nature13946
2. Yarveysi, F., et al. 2023. Block-level vulnerability assessment reveals disproportionate impacts of natural hazards. *Nature Communications*. https://www.nature.com/articles/s41467-023-41888-0
3. Abatzoglou, J. T., & Williams, A. P. 2016. Impact of climate change on wildfire across western U.S. forests. *PNAS*. https://www.pnas.org/doi/10.1073/pnas.1607171113
4. Cutter, S. L., Boruff, B. J., & Shirley, W. L. 2003. Social vulnerability to environmental hazards. *Social Science Quarterly*. https://doi.org/10.1111/1540-6237.8402002
5. Kreibich, H., et al. 2014. Costing natural hazards. *Nature Climate Change*. https://www.nature.com/articles/nclimate2126
6. FEMA National Risk Index. https://hazards.fema.gov/nri/
