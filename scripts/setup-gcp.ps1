# ============================================================================
# Senda - Google Cloud Run Setup Script (PowerShell)
# ============================================================================
# This script sets up Workload Identity Federation for GitHub Actions
# and creates the necessary service account and IAM bindings.
#
# Prerequisites:
#   - Google Cloud SDK (gcloud) installed and authenticated
#   - A GCP project with billing enabled
#   - Owner or Editor role on the project
#
# Usage:
#   .\scripts\setup-gcp.ps1 -ProjectId "your-project-id" -GitHubOrg "fariassdev" -GitHubRepo "senda"
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,

    [Parameter(Mandatory=$true)]
    [string]$GitHubOrg,

    [Parameter(Mandatory=$true)]
    [string]$GitHubRepo,

    [string]$Region = "us-central1"
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceAccountName = "github-actions-deploy"
$PoolName = "github-actions-pool"
$ProviderName = "github-provider"

# Helper functions
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-Success { param($Message) Write-Host "[SUCCESS] $Message" -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host "[WARNING] $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

Write-Host ""
Write-Info "=============================================="
Write-Info "Senda - GCP Setup for GitHub Actions"
Write-Info "=============================================="
Write-Info "Project: $ProjectId"
Write-Info "GitHub: $GitHubOrg/$GitHubRepo"
Write-Info "Region: $Region"
Write-Host ""

# Step 1: Set active project
Write-Info "Step 1/8: Setting active project..."
gcloud config set project $ProjectId
if ($LASTEXITCODE -ne 0) { throw "Failed to set project" }
Write-Success "Project set to $ProjectId"

# Step 2: Enable required APIs
Write-Host ""
Write-Info "Step 2/8: Enabling required APIs..."
gcloud services enable `
    run.googleapis.com `
    artifactregistry.googleapis.com `
    iam.googleapis.com `
    iamcredentials.googleapis.com `
    cloudresourcemanager.googleapis.com `
    --quiet
if ($LASTEXITCODE -ne 0) { throw "Failed to enable APIs" }
Write-Success "APIs enabled successfully"

# Step 3: Create service account
Write-Host ""
Write-Info "Step 3/8: Creating service account..."
$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

$existingAccount = gcloud iam service-accounts describe $ServiceAccountEmail 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Warning "Service account already exists, skipping creation"
} else {
    gcloud iam service-accounts create $ServiceAccountName `
        --display-name="GitHub Actions Deploy Service Account" `
        --description="Service account for deploying from GitHub Actions"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create service account" }
    Write-Success "Service account created"
}

# Step 4: Grant IAM roles to service account
Write-Host ""
Write-Info "Step 4/8: Granting IAM roles to service account..."
$Roles = @(
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser"
)

foreach ($role in $Roles) {
    Write-Info "  Granting $role..."
    gcloud projects add-iam-policy-binding $ProjectId `
        --member="serviceAccount:$ServiceAccountEmail" `
        --role="$role" `
        --quiet 2>&1 | Out-Null
}
Write-Success "IAM roles granted"

# Step 5: Create Workload Identity Pool
Write-Host ""
Write-Info "Step 5/8: Creating Workload Identity Pool..."
$existingPool = gcloud iam workload-identity-pools describe $PoolName --location="global" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Warning "Workload Identity Pool already exists, skipping creation"
} else {
    gcloud iam workload-identity-pools create $PoolName `
        --location="global" `
        --display-name="GitHub Actions Pool" `
        --description="Pool for GitHub Actions Workload Identity Federation"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Workload Identity Pool" }
    Write-Success "Workload Identity Pool created"
}

# Step 6: Create Workload Identity Provider
Write-Host ""
Write-Info "Step 6/8: Creating Workload Identity Provider..."
$existingProvider = gcloud iam workload-identity-pools providers describe $ProviderName `
    --location="global" `
    --workload-identity-pool="$PoolName" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Warning "Workload Identity Provider already exists, skipping creation"
} else {
    gcloud iam workload-identity-pools providers create-oidc $ProviderName `
        --location="global" `
        --workload-identity-pool="$PoolName" `
        --display-name="GitHub Provider" `
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" `
        --attribute-condition="assertion.repository_owner == '$GitHubOrg'" `
        --issuer-uri="https://token.actions.githubusercontent.com"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Workload Identity Provider" }
    Write-Success "Workload Identity Provider created"
}

# Step 7: Configure IAM binding for Workload Identity
Write-Host ""
Write-Info "Step 7/8: Configuring IAM binding for Workload Identity..."
$PoolId = gcloud iam workload-identity-pools describe $PoolName `
    --location="global" `
    --format="value(name)"

gcloud iam service-accounts add-iam-policy-binding $ServiceAccountEmail `
    --role="roles/iam.workloadIdentityUser" `
    --member="principalSet://iam.googleapis.com/$PoolId/attribute.repository/$GitHubOrg/$GitHubRepo" `
    --quiet 2>&1 | Out-Null

Write-Success "IAM binding configured"

# Step 8: Create Artifact Registry repository
Write-Host ""
Write-Info "Step 8/8: Creating Artifact Registry repository..."
$existingRepo = gcloud artifacts repositories describe senda --location="$Region" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Warning "Artifact Registry repository already exists"
} else {
    gcloud artifacts repositories create senda `
        --repository-format=docker `
        --location="$Region" `
        --description="Docker repository for Senda API"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Artifact Registry" }
    Write-Success "Artifact Registry repository created"
}

# Get full provider name for output
$ProviderFullName = gcloud iam workload-identity-pools providers describe $ProviderName `
    --location="global" `
    --workload-identity-pool="$PoolName" `
    --format="value(name)"

# Output GitHub secrets
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Success "Setup complete! Configure these GitHub secrets:"
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "GCP_PROJECT_ID:" -ForegroundColor Yellow
Write-Host "  $ProjectId" -ForegroundColor Green
Write-Host ""
Write-Host "WIF_PROVIDER:" -ForegroundColor Yellow
Write-Host "  $ProviderFullName" -ForegroundColor Green
Write-Host ""
Write-Host "WIF_SERVICE_ACCOUNT:" -ForegroundColor Yellow
Write-Host "  $ServiceAccountEmail" -ForegroundColor Green
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Info "Next Steps:"
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Add the above secrets to your GitHub repository:"
Write-Host "   Settings -> Secrets and variables -> Actions -> New repository secret"
Write-Host ""
Write-Host "2. Create GitHub environments:"
Write-Host "   Settings -> Environments -> New environment"
Write-Host "   - Create 'staging' (no protection rules)"
Write-Host "   - Create 'production' (add required reviewers)"
Write-Host ""
Write-Host "3. Deploy Terraform infrastructure:"
Write-Host "   cd terraform"
Write-Host "   cp terraform.tfvars.example terraform.tfvars"
Write-Host "   # Edit terraform.tfvars with your project_id"
Write-Host "   terraform init"
Write-Host "   terraform plan"
Write-Host "   terraform apply"
Write-Host ""
Write-Host "4. Push to develop branch to test staging deployment"
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Success "GCP setup complete!"
Write-Host "============================================================================" -ForegroundColor Cyan
