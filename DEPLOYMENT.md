# Senda - Cloud Run Deployment Guide

This guide covers deploying the Senda API to Google Cloud Run with staging and production environments using Terraform and GitHub Actions.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Initial Setup](#initial-setup)
- [GitHub Configuration](#github-configuration)
- [Terraform Deployment](#terraform-deployment)
- [CI/CD Workflow](#cicd-workflow)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** (`gcloud`) installed and authenticated
3. **Terraform** >= 1.0 installed
4. **Docker** installed (for local testing)
5. **GitHub repository** configured (`fariassdev/senda`)

### Verify installations

```bash
# Check gcloud
gcloud --version

# Check Terraform
terraform --version

# Check Docker
docker --version

# Authenticate gcloud
gcloud auth login
gcloud auth application-default login
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              GitHub                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   develop    │───▶│    Build     │───▶│   Staging    │               │
│  │   branch     │    │    Image     │    │   Deploy     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │     main     │───▶│    Build     │───▶│  Production  │ (approval)   │
│  │   branch     │    │    Image     │    │   Deploy     │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Google Cloud Platform                            │
│                                                                          │
│  ┌──────────────────────┐                                               │
│  │   Artifact Registry   │                                               │
│  │   (Docker Images)     │                                               │
│  └──────────────────────┘                                               │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐                   │
│  │   Cloud Run          │    │   Cloud Run          │                   │
│  │   (staging)          │    │   (production)       │                   │
│  │   • 1 CPU, 512Mi     │    │   • 2 CPU, 1Gi       │                   │
│  │   • 0-10 instances   │    │   • 1-100 instances  │                   │
│  └──────────────────────┘    └──────────────────────┘                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **Artifact Registry** | Stores Docker images |
| **Cloud Run (staging)** | Pre-production environment, auto-deploys from develop |
| **Cloud Run (production)** | Production environment, deploys from main with approval |
| **Workload Identity Federation** | Secure, keyless authentication from GitHub Actions |

---

## Initial Setup

### 1. Run the GCP Setup Script

The setup script configures all necessary GCP resources:

```bash
# Make the script executable (on Unix/macOS)
chmod +x scripts/setup-gcp.sh

# Run the setup script
./scripts/setup-gcp.sh <PROJECT_ID> <GITHUB_ORG> <GITHUB_REPO>

# Example:
./scripts/setup-gcp.sh my-senda-project fariassdev senda
```

**On Windows (Git Bash or WSL):**
```bash
bash scripts/setup-gcp.sh my-senda-project fariassdev senda
```

**On Windows (Powershell):**
```powershell
.\scripts\setup-gcp.ps1 -ProjectId "my-senda-project" -GitHubOrg "fariassdev" -GitHubRepo "senda"
```

The script will:
1. Enable required GCP APIs
2. Create a service account for GitHub Actions
3. Configure Workload Identity Federation
4. Create an Artifact Registry repository
5. Output the secrets needed for GitHub

### 2. Note the Output Values

The script outputs three values you'll need for GitHub:

```
GCP_PROJECT_ID: your-project-id
WIF_PROVIDER: projects/123456789/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
WIF_SERVICE_ACCOUNT: github-actions-deploy@your-project-id.iam.gserviceaccount.com
```

---

## GitHub Configuration

### 1. Add Repository Secrets

Go to your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `WIF_PROVIDER` | Full Workload Identity Provider path |
| `WIF_SERVICE_ACCOUNT` | Service account email |

### 2. Create GitHub Environments

Go to **Settings → Environments** and create:

#### Staging Environment
- Name: `staging`
- No protection rules required
- Auto-deploys on push to `develop` branch

#### Production Environment
- Name: `production`
- Enable **Required reviewers** (add yourself or team members)
- Optionally add **Wait timer** (e.g., 5 minutes)
- Only deploys after approval

---

## Terraform Deployment

### 1. Initialize Terraform

```bash
cd terraform

# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your project ID
# On Windows: notepad terraform.tfvars
# On Unix: nano terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
project_id = "your-actual-project-id"
region     = "us-central1"
app_name   = "senda"
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### 3. Verify Deployment

After `terraform apply`, you'll see outputs:

```
staging_url = "https://senda-staging-xxxxx-uc.a.run.app"
production_url = "https://senda-production-xxxxx-uc.a.run.app"
artifact_registry = "us-central1-docker.pkg.dev/your-project/senda"
```

> **Note:** The Cloud Run services are created but will only work after the first Docker image is pushed via GitHub Actions.

---

## CI/CD Workflow

### Automatic Deployments

| Branch | Environment | Trigger | Approval Required |
|--------|-------------|---------|-------------------|
| `develop` | Staging | Push | No |
| `main` | Production | Push | Yes |

### Manual Deployments

You can also trigger deployments manually:

1. Go to **Actions** → **Deploy to Cloud Run**
2. Click **Run workflow**
3. Select environment (staging or production)
4. Click **Run workflow**

### Workflow Steps

1. **Build Job**
   - Authenticates using Workload Identity Federation
   - Builds Docker image
   - Pushes to Artifact Registry with SHA and environment tags

2. **Deploy Job**
   - Deploys the new image to Cloud Run
   - Updates service URL in workflow summary

---

## Environment Variables

### Required Environment Variables

Configure these in GCP Console or via Terraform:

| Variable | Description | Required |
|----------|-------------|----------|
| `APP_ENV` | Application environment (`dev`, `prod`) | Yes (auto-set) |
| `POSTGRES_HOST` | Database host | Yes |
| `POSTGRES_PORT` | Database port | Yes |
| `POSTGRES_USER` | Database username | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `POSTGRES_DB` | Database name | Yes |
| `JWT_SECRET_KEY` | JWT signing secret | Yes |
| `SECRET_KEY` | Application secret | Yes |
| `GEMINI_API_KEY` | Gemini AI API key | Optional |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 | Optional |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for S3 | Optional |

### Setting Environment Variables

#### Option 1: Via GCP Console

1. Go to [Cloud Run](https://console.cloud.google.com/run)
2. Click on your service (staging or production)
3. Click **Edit & Deploy New Revision**
4. Under **Variables & Secrets**, add environment variables
5. Click **Deploy**

#### Option 2: Via Terraform

Add to `terraform.tfvars`:

```hcl
staging_env_vars = {
  "POSTGRES_HOST"     = "your-staging-db"
  "POSTGRES_PORT"     = "5432"
  "POSTGRES_USER"     = "postgres"
  "POSTGRES_PASSWORD" = "staging-password"
  "POSTGRES_DB"       = "senda_staging"
  "JWT_SECRET_KEY"    = "your-jwt-secret"
  "SECRET_KEY"        = "your-secret-key"
}

production_env_vars = {
  "POSTGRES_HOST"     = "your-production-db"
  "POSTGRES_PORT"     = "5432"
  "POSTGRES_USER"     = "postgres"
  "POSTGRES_PASSWORD" = "production-password"
  "POSTGRES_DB"       = "senda_production"
  "JWT_SECRET_KEY"    = "your-jwt-secret"
  "SECRET_KEY"        = "your-secret-key"
}
```

Then run `terraform apply`.

#### Option 3: GCP Secret Manager (Recommended for Production)

For sensitive values, use GCP Secret Manager:

```bash
# Create a secret
gcloud secrets create postgres-password \
    --replication-policy="automatic"

# Add a version
echo -n "your-password" | gcloud secrets versions add postgres-password --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding postgres-password \
    --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

## Troubleshooting

### Common Issues

#### 1. Workload Identity Authentication Failed

```
Error: Unable to acquire impersonated credentials
```

**Solution:** Verify the WIF_PROVIDER and WIF_SERVICE_ACCOUNT secrets are correct. Re-run the setup script if needed.

#### 2. Docker Push Permission Denied

```
Error: denied: Permission "artifactregistry.repositories.uploadArtifacts" denied
```

**Solution:** Ensure the service account has `roles/artifactregistry.writer` role:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:github-actions-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"
```

#### 3. Cloud Run Deployment Failed

```
Error: Revision 'xxx' is not ready and cannot serve traffic
```

**Solution:** Check Cloud Run logs:

```bash
gcloud run services logs read senda-staging --region=us-central1 --limit=50
```

#### 4. Health Check Failing

```
Error: Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable
```

**Solution:** Ensure your app:
- Binds to `0.0.0.0:8000`
- The `/api/health-check` endpoint responds within 3 seconds
- All required environment variables are set

#### 5. Terraform State Issues

```
Error: Error acquiring the state lock
```

**Solution:**
```bash
terraform force-unlock LOCK_ID
```

### Useful Commands

```bash
# View Cloud Run logs
gcloud run services logs read senda-staging --region=us-central1

# Describe service
gcloud run services describe senda-staging --region=us-central1

# List revisions
gcloud run revisions list --service=senda-staging --region=us-central1

# Check Docker image
gcloud artifacts docker images list us-central1-docker.pkg.dev/YOUR_PROJECT/senda

# Test locally
docker build -t senda:local .
docker run -p 8000:8000 --env-file .env.dev senda:local
```

---

## Cost Optimization

### Free Tier Limits (per month)

- **2 million requests**
- **360,000 GB-seconds** of memory
- **180,000 vCPU-seconds** of compute time
- **1 GB outbound data** transfer (within North America)

### Tips

1. **Use `us-central1`, `us-east1`, or `us-west1`** for free tier eligibility
2. **Set min instances to 0** for staging to avoid costs when idle
3. **Enable CPU idle** for staging (CPU only allocated during requests)
4. **Monitor usage** in GCP Console → Cloud Run → Metrics

---

## Security Best Practices

1. ✅ **Workload Identity Federation** - No stored service account keys
2. ✅ **Docs disabled in production** - API documentation not exposed
3. ✅ **Environment-specific secrets** - Different credentials per environment
4. ✅ **Manual production approval** - Required for production deployments
5. ✅ **Minimal instance permissions** - Service account has only required roles

---

## Support

For issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Cloud Run logs
3. Check GitHub Actions workflow runs
4. Open an issue in the repository
