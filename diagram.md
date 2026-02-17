## 1. Infrastructure Architecture
This diagram illustrates the Azure network topology, including the Bootstrap layer for state management and the Main Infrastructure.

```mermaid
flowchart TB
    %% Define Styles
    classDef user fill:#000,stroke:#000,color:#fff
    classDef compute fill:#0078D4,stroke:#005A9E,color:#fff
    classDef db fill:#68217A,stroke:#3E1F63,color:#fff
    classDef storage fill:#0072C6,stroke:#004D85,color:#fff
    classDef security fill:#D13438,stroke:#A4262C,color:#fff
    classDef net fill:#E1F0FA,stroke:#0078D4,stroke-dasharray: 5 5
    classDef plain fill:#fff,stroke:#999,stroke-dasharray: 5 5

    UserNode((👤 User / Internet)):::user
    
    subgraph AzureCloud["☁️ Azure Cloud (West Europe)"]
        style AzureCloud fill:#F3F2F1,stroke:#0078D4
        
        subgraph Bootstrap["🏗️ Bootstrap Infrastructure (State Management)"]
            style Bootstrap fill:#fff,stroke:#666,stroke-dasharray: 5 5
            TFStateSA[("📦 Storage Account<br/>(Terraform State)")]:::storage
        end

        subgraph MainInfra["🚀 Main Infrastructure (orbit-dev-rg)"]
            style MainInfra fill:#fff,stroke:#666,stroke-dasharray: 5 5

            subgraph VNet["🌐 VNet: orbit-dev-vnet (10.1.0.0/16)"]
                style VNet fill:#fff,stroke:#0078D4

                subgraph BackendSubnet["Backend Subnet (10.1.1.0/24)"]
                    style BackendSubnet fill:#E1F0FA,stroke:#0078D4
                    AKS["☸️ AKS Cluster<br/>(Nodes: Standard_B2s)"]:::compute
                end

                subgraph DBSubnet["DB Subnet (10.1.2.0/24)"]
                    style DBSubnet fill:#E1F0FA,stroke:#0078D4
                    Postgres[("🐘 PostgreSQL<br/>Flexible Server")]:::db
                    
                    subgraph NSG["🛡️ Network Security Group"]
                        style NSG fill:#FFF0F0,stroke:#D13438
                        Rule1["✅ Allow: 5432 (From Backend)"]:::security
                        Rule2["⛔ Deny: All VNet Inbound"]:::security
                    end
                end
                
                DNS["📖 Private DNS Zone<br/>(privatelink.postgres...)"]:::plain
            end
        end
    end

    UserNode ==>|HTTPS / 443| AKS
    AKS ==>|TCP / 5432| Postgres
    NSG -.-o|Applied to| DBSubnet
    DNS -.-o|Resolution Link| VNet
    TFStateSA -.->|Stores State| MainInfra
```

```mermaid
flowchart TD
    %% Styles
    classDef trigger fill:#F9A825,stroke:#C77900,color:#fff
    classDef step fill:#2088FF,stroke:#005CC5,color:#fff
    classDef tf fill:#7B42BC,stroke:#5A308C,color:#fff
    classDef destroy fill:#D13438,stroke:#A4262C,color:#fff
    classDef azure fill:#0078D4,stroke:#005A9E,color:#fff
    classDef manual fill:#607D8B,stroke:#455A64,color:#fff

    Dev[👤 Developer]

    %% 1. Bootstrap Process
    subgraph Bootstrap_Process ["🏗️ 1. Bootstrap (One-Time Manual Setup)"]
        style Bootstrap_Process fill:#F3F2F1,stroke:#607D8B,stroke-dasharray: 5 5
        
        BootInit[("⚙️ TF Init")]:::tf
        BootApply[("🚀 TF Apply")]:::tf
        BootOutputs[("📄 Outputs<br/>(RG, SA Name)")]:::manual
        
        ConfigSecrets[("🔐 Configure GitHub Secrets")]:::manual
    end

    subgraph GitHub ["🐙 2. GitHub Actions Workflow (CI/CD)"]
        style GitHub fill:#F6F8FA,stroke:#24292F
        
        %% Triggers
        subgraph Triggers ["Triggers"]
            style Triggers fill:#fff,stroke:#ccc,stroke-dasharray: 5 5
            TriggerPR{{"🔀 Pull Request"}}:::trigger
            TriggerPush{{"🚀 Push to Main"}}:::trigger
            TriggerManual{{"⚠️ Manual Dispatch"}}:::trigger
        end

        %% Common Steps
        Secrets[("🔐 Secrets Injection")]:::step
        Init[("⚙️ Terraform Init")]:::tf
        Validate[("✅ Terraform Validate")]:::tf
        
        %% Logic
        Decision{{"❓ Event Condition"}}

        %% Branches
        subgraph PR_Flow ["PR Flow"]
            style PR_Flow fill:#fff,stroke:#ccc,stroke-dasharray: 5 5
            PlanOnly["📄 Plan"]:::tf
        end

        subgraph Main_Flow ["Main Branch Flow"]
            style Main_Flow fill:#fff,stroke:#ccc,stroke-dasharray: 5 5
            PlanApply["📄 Plan"]:::tf
            Apply["🚀 Apply"]:::tf
        end

        subgraph Destroy_Flow ["Manual Destroy"]
            style Destroy_Flow fill:#fff,stroke:#ccc,stroke-dasharray: 5 5
            PlanDestroy["📄 Plan (-destroy)"]:::tf
            Destroy["🔥 Destroy"]:::destroy
        end
    end

    AzSub[☁️ Azure Subscription]:::azure

    %% Connections
    Dev -->|Local CLI| BootInit
    BootInit --> BootApply --> BootOutputs
    BootOutputs --> ConfigSecrets
    ConfigSecrets -.->|Available for| Secrets

    Dev --> TriggerPR
    Dev --> TriggerPush
    Dev --> TriggerManual

    TriggerPR --> Secrets
    TriggerPush --> Secrets
    TriggerManual --> Secrets

    Secrets --> Init --> Validate --> Decision

    Decision -- "Pull Request" --> PlanOnly
    Decision -- "Push to Main" --> PlanApply --> Apply
    Decision -- "Manual (Destroy=true)" --> PlanDestroy --> Destroy

    %% Outputs
    PlanOnly -.->|Review| Dev
    Apply -->|Deploy| AzSub
    Destroy -.->|Delete| AzSub
    BootApply -->|Create State Storage| AzSub
```