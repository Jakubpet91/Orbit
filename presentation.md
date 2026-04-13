---
marp: true
theme: gaia
class: lead
backgroundColor: #fff
backgroundImage: url('https://marp.app/assets/hero-background.svg')
style: |
  section {
    font-family: 'Segoe UI', sans-serif;
  }
  h1 {
    color: #0078D4;
  }
  strong {
    color: #0078D4;
  }
---

# Accelerating Azure Adoption with IaC

## Strategy Proposal for Contoso
### DevOps Engineer Candidate

---

# Where is Contoso Today?

- **Enterprise Scale:** Multiple departments & legacy applications.
- **Current State:** Early stages of Microsoft Azure adoption.
- **Challenge:** Manual deployments are slow, error-prone, and inconsistent.
- **Goal:** Standardized, secure Landing Zones deployed via code.

---

# What is Infrastructure as Code?

> "Managing infrastructure through code files rather than manual hardware configuration or interactive configuration tools."

- **Concept:** 'Blueprints' for your cloud environment.
- **Key Shift:** Treating servers like software.
- **Result:** Versioned, testable, and repeatable infrastructure.

---

# Business Benefits

1. **Speed:** Deploy complex environments in minutes.
2. **Consistency:** Dev = Test = Prod. No more "it works on my machine".
3. **Cost Efficiency:** Tear down unused resources instantly.
4. **Security:** Git history tracks every change (Audit trail).

---

# IaC Options in Azure

| Tool | Type | Best For |
| :--- | :--- | :--- |
| **Bicep** | Native | Azure-only shops |
| **Terraform** | Open Source | Multi-cloud, Hybrid (Recommended) |
| **Pulumi** | Code | Devs who want to use Python/C# |
| **Ansible** | Config Mgmt | OS configuration |

---

# Pros & Cons

<div class="columns">
<div>

### ✅ Pros
- Disaster Recovery
- Documentation as Code
- Scalability
- Modularity

</div>
<div>

### ⚠️ Challenges
- Learning Curve (HCL)
- State Management
- Maintenance Overhead

</div>
</div>

---

# Prerequisites for Success

- **Version Control:** Git (GitHub / GitLab)
- **CI/CD Pipeline:** Automated Runners (GitHub Actions)
- **Governance:** Policies & Naming Conventions
- **Skillset:** Training the team in Terraform

---

# Technical Demo Strategy

### What I built for you today:
- **Terraform** Modular Infrastructure
- **GitHub Actions** Pipeline
- **AKS + PostgreSQL** Secure Architecture
- **Hub & Spoke** Network Model

---

# Q & A

Thank you for your attention.