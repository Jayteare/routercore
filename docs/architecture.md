# Architecture

```mermaid
flowchart TD
    A["User Request"] --> B["Router Proposal"]
    B --> C["Schema Validator"]
    C --> D["Policy Engine"]
    D --> E{"Final Decision"}
    E --> F["Accepted Route"]
    E --> G["Clarification"]
    E --> H["Confirmation"]
    E --> I["Rejection"]
    E --> J["Fallback"]
    F --> K["Orchestrator Preview"]
    G --> L["User Answer / Additional Context"]
    L --> B
    H --> M["User Confirmation"]
    M --> N{"Confirmed?"}
    N -->|"Yes"| K
    N -->|"No"| I
    I --> O["Stop / No Execution"]
    J --> P["Manual Review / Larger Orchestrator"]
    K --> Q["No Real Execution"]
```

The router proposes a route, but validation and policy decide the final state. Clarification loops gather missing context and route again. Rejected requests stop without execution, and fallback requests move to manual review or a larger orchestrator. Accepted or confirmed routes generate previews only; the orchestrator does not execute real cloud or infrastructure actions.
