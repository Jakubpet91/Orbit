## 1. Infrastructure Architecture

This diagram illustrates the Azure network topology, including the Bootstrap layer for state management and the Main Infrastructure.

```mermaid
flowchart TD
    %% --- DEFINICE BAREV A STYLŮ ---
    %% Kontejnery (Bílé/Světlé pozadí -> ČERNÝ TEXT)
    classDef container fill:#fff,stroke:#333,color:#000
    classDef azure fill:#E1F0FA,stroke:#0078D4,color:#000
    
    %% Zdroje (Tmavé pozadí -> BÍLÝ TEXT)
    classDef resource fill:#326CE5,stroke:#326CE5,color:#fff
    classDef db fill:#336791,stroke:#336791,color:#fff
    classDef storage fill:#289028,stroke:#289028,color:#fff
    
    %% Security (Světle červené pozadí -> ČERVENÝ TEXT)
    classDef warning fill:#FFF4F4,stroke:#D13438,stroke-dasharray: 5 5,color:#D13438

    User((👤 User)):::container

    %% --- INFRASTRUKTURA ---
    subgraph Cloud["☁️ Azure Cloud"]
        direction TB
        
        %% Bootstrap
        subgraph Bootstrap["🏗️ Bootstrap (State Mgmt)"]
            TFState[("📦 Storage Account<br/>tfstate container")]:::storage
        end

        %% Main Infrastructure
        subgraph MainInfra["🚀 Main Infrastructure"]
            
            subgraph VNet["🌐 VNet: spoke1<br/>"]
                
                subgraph BE_Sub["Backend Subnet<br/>(10.0.1.0/24)"]
                    Ingress["🌐 Ingress Controller<br/>(Public IP / Frontend)"]:::resource
                    App["⚙️ App Pods"]:::resource
                end

                subgraph DB_Sub["DB Subnet<br/>(10.0.2.0/24)"]
                    Postgres[("🐘 PostgreSQL<br/>Flexible Server")]:::db
                    NSG["🛡️ NSG Rules<br/>✅ Allow: 5432<br/>Source: Backend Subnet"]:::warning
                end
            end
        end
    end

    %% --- PROPOJENÍ (S POPISKY) ---
    User ==> Ingress
    Ingress -->|Routing| App
    App ==>|TCP/5432| Postgres
    
    %% Logické vazby
    NSG -.-o Postgres
    TFState -.->|Stores State for| MainInfra

    %% --- APLIKACE STYLŮ ---
    class Cloud,MainInfra,Bootstrap container
    class VNet,BE_Sub,DB_Sub azure
```

```mermaid
flowchart TD
    %% --- STYLOVÁNÍ ---
    %% Manuální kroky - Žlutá, černý text
    classDef manual fill:#FFF9C4,stroke:#FBC02D,color:#000000
    %% GitHub kroky - Tmavá, bílý text
    classDef gh fill:#24292F,stroke:#000,color:#fff
    %% Terraform akce - Fialová, bílý text
    classDef terraform fill:#7B42BC,stroke:#5A308C,color:#fff
    %% Azure zdroje - Modrá, bílý text
    classDef azure fill:#0078D4,stroke:#005A9E,color:#fff

    %% --- AKTÉŘI ---
    Dev[👤 DevOps Engineer]

    %% --- 1. FÁZE: BOOTSTRAP ---
    subgraph Phase1["1️⃣ Fáze: Bootstrap (Local)"]
        style Phase1 fill:#F5F5F5,stroke:#999,stroke-dasharray: 5 5,color:#000000
        InitLocal["tf init & apply"]:::manual
        CreateSA["Vytvoření Storage Account<br/>pro tfstate"]:::azure
        GetCreds["Získání Azure Credentials<br/>(Service Principal)"]:::manual
    end

    %% --- 2. FÁZE: GITHUB ACTIONS ---
    subgraph Phase2["2️⃣ Fáze: GitHub Actions (CI/CD)"]
        style Phase2 fill:#E1F0FA,stroke:#0078D4,color:#000000
        
        Secrets["🔐 GitHub Secrets<br/>(ARM_CLIENT_ID...)"]:::gh
        
        subgraph Pipeline["🔄 Terraform Workflow"]
            style Pipeline fill:#ffffff,stroke:#ccc,color:#000000
            TFInit["terraform init<br/>(backend=azurerm)"]:::terraform
            TFPlan["terraform plan"]:::terraform
            TFApply["terraform apply<br/>(auto-approve)"]:::terraform
        end
    end

    %% --- CÍL ---
    TargetEnv[("☁️ Azure Resources<br/>(AKS, VNet, DB)")]:::azure

    %% --- TOK ---
    Dev -->|1. Run once| InitLocal
    InitLocal --> CreateSA
    CreateSA -.->|State Storage| TFInit
    
    Dev -->|2. Configure| Secrets
    Secrets -.-> Pipeline

    Dev -->|3. Git Push| Pipeline
    TFInit --> TFPlan --> TFApply
    TFApply -->|Deploy| TargetEnv
```