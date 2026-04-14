# InfraGuard Sentinel - AI-Powered Terraform Analyzer

Autonomous AI agent for analyzing Terraform code using Google Gemini API.
Supports **two architectures**: local CLI development and production webhooks (GitHub/GitLab).

## Features

- ✅ **AI-Powered Reviews** - Gemini 2.5 Flash analysis
- ✅ **Security-First** - Detects security risks
- ✅ **Cost Optimization** - Suggests cost savings
- ✅ **Documentation Check** - Warns about missing docs
- ✅ **Docker Support** - No local Python dependencies
- ✅ **Render-Ready** - Deployment-ready
- ✅ **Webhooks** - GitHub and GitLab integration

## Architecture

### File Structure

```
infraguard-bot/
├── shared.py              # Shared Gemini logic (SINGLE SOURCE OF TRUTH)
├── dev.py                 # Local development CLI (python dev.py)
├── main.py                # Production FastAPI server (uvicorn main:app)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container image
├── docker-compose.yml     # Local dev: runs `tail -f /dev/null` + `docker exec ... python dev.py`
├── test.ps1               # Fast testing script (FastMode - container stays running)
├── .env.template          # Configuration template
└── .env                   # Configuration (GEMINI_API_KEY, tokens, etc) - in .gitignore
```

### Mode 1: Local Development (CLI)

**Fast Development Mode** - Container stays running on background:

```powershell
# First time: starts container + runs analysis (~5s)
.\test.ps1

# Subsequent runs: just analysis (~2-3s)
.\test.ps1

# Options:
.\test.ps1 -rebuild     # Force rebuild image (after package changes)
.\test.ps1 -stop        # Stop container when done

# Manual control:
docker-compose up -d    # Start container
docker-compose down     # Stop container
```

**Output**: Saved to `/tmp/gemini_response.txt` in container

### Mode 2: Production (Webhooks)

```bash
# On Render: automatic build and deployment
# Just push to main branch, Render builds Dockerfile automatically

# Local production testing:
docker build .
docker run -p 8000:8000 -e GEMINI_API_KEY=... infraguard-bot-infraguard-sentinel
```

**Endpoints**:
- `POST /webhook` - GitHub PR analysis
- `POST /webhook/gitlab` - GitLab MR analysis  
- `GET /` - Service info
- `GET /health` - Health check

## Quick Start

### 1. Setup

```powershell
# Clone and setup
git clone <repo>
cd infraguard-bot

# Create .env from template
Copy-Item .env.template .env

# Edit .env and add your API keys:
# GEMINI_API_KEY=your-key
# GITHUB_TOKEN=optional-for-webhooks
# GITLAB_TOKEN=optional-for-webhooks

notepad .env
```

### 2. Local Testing (Dev Mode)

```powershell
# Build image and run analysis
docker-compose build
docker-compose up -d
docker-compose exec infraguard-sentinel python dev.py /code

# OR use the test runner:
.\test.ps1
```

### 3. Production Deployment (Webhooks)

```bash
# On Render or your host:
docker-compose -f docker-compose.prod.yml up

# For GitHub: Set webhook to https://your-app.render.com/webhook
# For GitLab: Set webhook to https://your-app.render.com/webhook/gitlab
```

## Shared Core Logic (shared.py)

Both `dev.py` and `main.py` import from `shared.py`:

```python
from shared import load_terraform_files, analyze_with_gemini, load_readme

# Load all .tf files as single string (batch mode)
terraform_content = load_terraform_files("/path/to/terraform")

# Single Gemini API call
response = await analyze_with_gemini(
    terraform_content=terraform_content,
    gemini_api_key=api_key,
    webhook_diff=None  # Optional: pass specific PR/MR diff instead
)
```

## API Configuration

### Google Gemini API

1. Go to https://ai.google.dev/
2. Create new API key
3. Add to `.env`:

```
GEMINI_API_KEY=your-api-key-here
```

### GitHub Integration

1. Go to Settings > Developer settings > Personal access tokens
2. Create token with `repo:status` and `repo:read` scopes
3. Add to `.env`:

```
GITHUB_TOKEN=ghp_xxxxx
```

### GitLab Integration

1. Go to Settings > Access Tokens
2. Create token with `api` and `read_repository` scopes  
3. Add to `.env`:

```
GITLAB_TOKEN=glpat_xxxxx
```

## Docker Management

```powershell
# Local development
docker-compose up -d       # Start container (keeps running)
docker-compose down        # Stop container
docker-compose logs -f     # View logs
docker-compose rebuild     # Rebuild image

# Production (Render)
# Render automatically:
# 1. Detects Dockerfile
# 2. Builds: docker build .
# 3. Runs: docker run -p 8000:8000 main:app
# Set env vars in Render dashboard: GEMINI_API_KEY, GITHUB_TOKEN, GITLAB_TOKEN
```

## Testing

### FastMode - Quick Local Tests (Container-based)

```powershell
# Quick test with auto container management (FastMode)
.\test.ps1

# Options:
.\test.ps1 -rebuild     # Force image rebuild
.\test.ps1 -stop        # Stop container after test
```

### Smart Diff Analysis - Token-Efficient Testing

**Requirements**: Terraform code location must be a git repository

```powershell
# FULL BATCH MODE - analyzes ALL .tf files (~4461 tokens)
docker-compose exec infraguard-sentinel python dev.py

# SMART DIFF MODE - analyzes only CHANGED files (~800 tokens, 82% reduction)
docker-compose exec infraguard-sentinel python dev.py --diff

# Analyze specific commit
docker-compose exec infraguard-sentinel python dev.py --diff HEAD~1

# Local testing (outside Docker)
python dev.py              # Full batch
python dev.py --diff       # Smart diff (requires git repo at C:\Users\jakub.petricek\Personal\Orbit)
```

**Token Estimation** - Logged automatically:
```
[TOKEN ESTIMATE] Batch mode: ~4461 tokens
[TOKEN ESTIMATE] Smart Diff mode: ~800 tokens
[TOKEN REDUCTION] vs full batch: ~78-85% saved!
```

**Docker Volume Configuration**:
```yaml
volumes:
  - C:\Users\jakub.petricek\Personal\Orbit:/code:ro
```
This mounts your Terraform repo as `/code` in the container. Smart Diff mode reads git history from this location.

## System Constraints

- **Single API Call**: All Terraform files loaded as ONE batch string per analysis
- **Quota-Aware**: Falls back to demo response if API quota exhausted (ResourceExhausted 429)
- **File Size**: Supports up to ~32K characters of Terraform code (single call limit)
- **Response Sections**: SECURITY, COSTS, DOCUMENTATION
- **Docker Context**: /code volume mounted read-only to `C:\Users\jakub.petricek\Personal\Orbit`
- **Smart Diff**: Requires git repository for `--diff` mode (analyzes only changed files + 10-line context)
- **Token Efficiency**: 
  - Full Batch: ~4461 tokens (all .tf files)
  - Smart Diff: ~800 tokens (only changes) = 82% reduction

## Troubleshooting

### Container won't start

```powershell
# Clean up and restart
docker-compose down --remove-orphans
docker-compose up --build -d
docker-compose logs -f
```

### Missing .env

```powershell
# Template provided
Copy-Item .env.template .env
```

### API Quota Spent

- Fallback response automatically triggered
- Model returns demo/example output
- No errors - graceful degradation
- Next day quota resets

### Webhook Not Working

- Check port 8000 is accessible: `curl http://localhost:8000/health`
- Verify Render deployment logs
- Confirm webhook URL is correct in GitHub/GitLab settings
- Check token permissions match repository access

## Chaos Testing Framework

InfraGuard includes **integrated chaos testing** for validating Sentinel's detection accuracy and Gemini's review capabilities. Single unified pipeline handles injection, detection, and AI review.

### Quick Start

```powershell
# Run test - random severity level
.\chaos.ps1

# Test specific levels
.\chaos.ps1 -Level low      # Small issues: expensive VM, missing tags
.\chaos.ps1 -Level medium   # Security warnings: disabled encryption, public access
.\chaos.ps1 -Level high     # Critical vulns: SSH open, hard-coded secrets

# Force rebuild image
.\chaos.ps1 -Level medium -Rebuild
```

### How It Works

The chaos testing pipeline is a 4-stage automated process:

```
STAGE 1: CHAOS INJECTION
  ↓
  Randomly selects .tf file, injects controlled error at severity level
  Injects realistic mistakes: cost optimization issues, security gaps, critical holes
  Parameters optimized with Gemini prompts for each level

STAGE 2: DETECTION ANALYSIS  
  ↓
  Commits injected code to chaos-testing branch
  Pushes to GitHub with token authentication
  Runs InfraGuard Sentinel smart diff analysis
  Measures detection accuracy & confidence

STAGE 3: AI REVIEW ANALYSIS
  ↓
  Gemini reviews the injected code
  Identifies security issues, cost problems, best practice violations  
  Generates human-readable analysis
  Helps validate review generator prompts

STAGE 4: EVALUATION
  ↓
  Reports: Detected? YES/NO
  Reports: Confidence score (0-100%)
  Reports: Severity match (correct level detected?)
  Full output saved to logs for debugging
```

### Severity Levels & Detection Rates

**LOW** (~65% detection)
- Change expensive VM SKU (cost optimization)
- Remove cost allocation tags (billing tracking)
- Increase backup retention (storage cost)
- Missing environment tags (resource management)

**MEDIUM** (~75% detection)
- Disable encryption at rest (compliance risk)
- Enable public network access (security exposure)
- Disable HTTPS requirement (data in transit)
- Weak TLS version (outdated crypto)
- Remove firewall rules (network exposure)

**HIGH** (~40% detection - more complex patterns)
- SSH port (22) open to internet (critical access hole)
- Hard-coded credentials (secret exposure)
- Storage rules allow all traffic (unrestricted access)
- Remove authentication dependency (bypass)
- Unrestricted egress rules (data exfiltration)

### Using Results for Debugging

Each run produces logs for prompt engineering:

```powershell
# Run and save output
.\chaos.ps1 -Level high  # Creates logs in temp directory

# Find the log
$log = Get-ChildItem $env:TEMP\chaos_*.log | Sort-Object LastWriteTime -Desc | Select-Object -First 1
Get-Content $log.FullName

# Analyze:
# 1. Did Sentinel detect correctly? (Stage 2)
# 2. Did Gemini review identify the issue? (Stage 3)
# 3. What was confidence score? (Stage 4)
```

### Repository Structure

Tests use the `chaos-testing` branch:
- Branch: https://github.com/Jakubpet91/Orbit/tree/chaos-testing
- Each test creates commit with injected error
- Changes auto-pushed via GitHub token authentication  
- Full commit history available for analysis

### Advanced: Integrating with test.ps1

The standard test.ps1 operates on clean code. To test chaos + detection:

```powershell
# Only for manual debugging - chaos.ps1 is the recommended script
.\chaos.ps1 -Level medium

# To integrate with your CI pipeline:
$result = .\chaos.ps1 -Level high
if ($LASTEXITCODE -eq 0) {
    Write-Host "Chaos test passed"
}
```

## Performance Notes

- **Batch Loading**: All .tf files concatenated into single string
- **Single Call**: One `model.generate_content()` per analysis
- **Time**: ~2-3 seconds per analysis (Gemini response)
- **Memory**: ~200MB container footprint
- **Storage**: Uses /tmp for response caching
- **Chaos Tests**: ~10-15 seconds per test (includes git operations)

## License

MIT - See LICENSE file

## Support

Issues? Submit to GitHub Issues or contact @infraguard-team
