# Architecture diagrams

Diagrams are Mermaid, so GitHub renders them directly. **All data are synthetic.**

## 1. End-to-end workflow

```mermaid
flowchart LR
    RAW["data/raw<br/>users CSV + workbook<br/>(read-only)"] --> AUD["01 Audit<br/>findings F1-F8"]
    AUD --> CLN["02 Cleaning<br/>13 logged changes<br/>as-of flags, maturity"]
    CLN --> CD["data/cleaned<br/>4 tables + 4 derived"]
    CD --> SQL["04 SQL<br/>34 queries (SQLite)"]
    CD --> PY["05 Python<br/>package, pipeline,<br/>5 notebooks"]
    CD --> BA["03 Business analytics<br/>6 modules"]
    SQL --> VER{{"Cross-check<br/>SQL = Python = Excel<br/>71 / 71 KPIs"}}
    PY --> VER
    BA --> VER
    BA --> XL["Excel workbooks<br/>+ Word / PDF report"]
    CD --> DB["06 Dashboard kit<br/>star schema + 117 DAX<br/>(no .pbix)"]
    BA --> STR["07 Growth strategy<br/>15 recommendations<br/>10 proposed experiments"]
    CD --> AI["08 AI Friction Detector<br/>rules, score, Streamlit"]
    classDef navy fill:#0B1F3A,color:#fff,stroke:#0B1F3A;
    classDef green fill:#E6F4EC,color:#0B1F3A,stroke:#2E8B57;
    class RAW,CD navy;
    class VER green;
```

## 2. Customer onboarding funnel (mature cohort, n = 9,116)

```mermaid
flowchart LR
    A["Registered<br/>9,116"] -->|70.5%| B["KYC completed<br/>6,429"]
    B -->|87.8%| C["Bank linked<br/>5,645"]
    C -->|76.9%| D["First deposit<br/>4,340"]
    D -->|79.8%| E["First trade<br/>3,462"]
    E -->|81.1%| F["Active 30d<br/>2,808"]
    A -. "KYC: 42.6% of all losses" .-> B
```

## 3. Data model for the dashboard (star schema)

```mermaid
erDiagram
    DimCampaign ||--o{ FactCustomer : CampaignKey
    DimCity     ||--o{ FactCustomer : CityKey
    DimDevice   ||--o{ FactCustomer : DeviceKey
    DimSegment  ||--o{ FactCustomer : SegmentKey
    DimCampaign ||--o{ FactActivity : CampaignKey
    DimCity     ||--o{ FactActivity : CityKey
    DimDevice   ||--o{ FactActivity : DeviceKey
    DimSegment  ||--o{ FactActivity : SegmentKey
    DimCampaign ||--o{ FactTicket   : CampaignKey
    DimCity     ||--o{ FactTicket   : CityKey
    DimDevice   ||--o{ FactTicket   : DeviceKey
    DimSegment  ||--o{ FactTicket   : SegmentKey
    DimDate     ||--o{ FactCustomer : RegistrationDate
    DimDate     ||--o{ FactActivity : ActivityMonthDate
    DimDate     ||--o{ FactTicket   : CreatedDate
```

All 15 relationships are one-to-many, single-direction (each fact carries the dimension keys, so there are no fact-to-fact links); `DimStage` is deliberately unrelated. Full table: [`06_dashboard/docs/Data_Model.md`](../../06_dashboard/docs/Data_Model.md).

## 4. AI Friction Detector

```mermaid
flowchart TB
    CSV["Synthetic CSVs<br/>users, tickets, monthly activity"] -->|build-db| DBS[("SQLite friction.db")]
    DBS -->|run-daily --as-of D| ENG["Rules engine<br/>stage, observed-lag windows,<br/>friction categories, data confidence"]
    ENG --> SCORE["Priority score 0-100<br/>(heuristic, not ML)"]
    SCORE --> RUNS[("customer_friction<br/>friction_snapshot<br/>friction_runs")]
    RUNS --> INS["Insights<br/>rule-based text; optional LLM re-wording"]
    RUNS --> RPT["Daily report folder<br/>exception CSV, newly flagged,<br/>by category, summary"]
    INS --> RPT
    RUNS --> APP["Streamlit dashboard"]
    INS --> APP
```

Detail: [`08_ai_friction_detector/docs/ARCHITECTURE.md`](../../08_ai_friction_detector/docs/ARCHITECTURE.md).

## 5. Where each deliverable lives

```mermaid
flowchart TB
    R["README.md"] --> D["documentation/"]
    R --> M01["01_data_audit"]
    R --> M02["02_data_cleaning"]
    R --> M03["03_business_analytics"]
    R --> M04["04_sql"]
    R --> M05["05_python"]
    R --> M06["06_dashboard"]
    R --> M07["07_growth_strategy"]
    R --> M08["08_ai_friction_detector"]
    R --> REP["reports/"]
    D --> REC["documentation/recruiter/"]
```
