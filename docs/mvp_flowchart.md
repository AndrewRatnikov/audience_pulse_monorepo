# High level system design for MVP

```Mermaid
flowchart TD
 A[Secrets / Config Manager\nExample: AWS Secrets Manager]
 B[User Interface\nWeb App for input and display]
 C[API Gateway\nHandles auth and rate limits]
 D[Core Service / Job Orchestrator\nRoutes and manages analysis tasks]
 E[Async Job Queue\nHandles background jobs e.g. Celery]
 F[Platform-Specific Data Access Modules]
 F1[Meta Graph API\nInstagram & Facebook]
 F2[YouTube Data API\nYouTube public data]
 G[NLP & Analysis Pipelines]
 G1[Summary Generation\nUses TextRank or BART-lite]
 G2[Keyword Extraction\nTF-IDF and frequency]
 G3[Sentiment Analysis\nVADER or fastText]
 G4[Interest Grouping\nKeyword co-occurrence]
 G5[Spam Filtering\nRemoves bot or irrelevant content]
 H[Output Generation Module\nGenerates text/markdown output]
 I[Result Cache\nTemporary store e.g. Redis]
 J[Observability Layer\nLogging, metrics, and tracing]


 A --> B
 B --> C
 C --> D
 D --> E
 E --> F
 F --> F1
 F --> F2
 F --> G
 G --> G1
 G --> G2
 G --> G3
 G --> G4
 G --> G5
 G --> H
 H --> I
 I --> B


 C --> J
 D --> J
 E --> J
 F --> J
 G --> J
 H --> J
 I --> J


 %% Styling for MVP simplifications/deferrals (red background)
 style A fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style C fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style E fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style G4 fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style G5 fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style I fill:#FFCCCC,stroke:#FF0000,stroke-width:2px
 style J fill:#FFCCCC,stroke:#FF0000,stroke-width:2px

```
