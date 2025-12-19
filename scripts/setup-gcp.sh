#!/bin/bash
set -euo pipefail

# ============================================================================
# Senda - Google Cloud Run Setup Script
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
#   ./scripts/setup-gcp.sh <PROJECT_ID> <GITHUB_ORG> <GITHUB_REPO>
#
# Example:
#   ./scripts/setup-gcp.sh my-gcp-project fariassdev senda
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check arguments
if [ "$#" -lt 3 ]; then
    log_error "Usage: $0 <PROJECT_ID> <GITHUB_ORG> <GITHUB_REPO>"
    echo ""
    echo "Example: $0 my-gcp-project fariassdev senda"
    exit 1
fi

PROJECT_ID="$1"
GITHUB_ORG="$2"
GITHUB_REPO="$3"
REGION="us-central1"
SERVICE_ACCOUNT_NAME="github-actions-deploy"
POOL_NAME="github-actions-pool"
PROVIDER_NAME="github-provider"

log_info "=============================================="
log_info "Senda - GCP Setup for GitHub Actions"
log_info "=============================================="
log_info "Project: $PROJECT_ID"
log_info "GitHub: $GITHUB_ORG/$GITHUB_REPO"
log_info "Region: $REGION"
echo ""

# Step 1: Set active project
log_info "Step 1/8: Setting active project..."
gcloud config set project "$PROJECT_ID"
log_success "Project set to $PROJECT_ID"

# Step 2: Enable required APIs
echo ""
log_info "Step 2/8: Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    iam.googleapis.com \
    iamcredentials.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --quiet
log_success "APIs enabled successfully"

# Step 3: Create service account
echo ""
log_info "Step 3/8: Creating service account..."
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    log_warning "Service account already exists, skipping creation"
else
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="GitHub Actions Deploy Service Account" \
        --description="Service account for deploying from GitHub Actions"
    log_success "Service account created"
fi

SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Step 4: Grant IAM roles to service account
echo ""
log_info "Step 4/8: Granting IAM roles to service account..."
ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.writer"
    "roles/iam.serviceAccountUser"
)

for role in "${ROLES[@]}"; do
    log_info "  Granting $role..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
        --role="$role" \
        --quiet >/dev/null
done
log_success "IAM roles granted"

# Step 5: Create Workload Identity Pool
echo ""
log_info "Step 5/8: Creating Workload Identity Pool..."
if gcloud iam workload-identity-pools describe "$POOL_NAME" \
    --location="global" &>/dev/null; then
    log_warning "Workload Identity Pool already exists, skipping creation"
else
    gcloud iam workload-identity-pools create "$POOL_NAME" \
        --location="global" \
        --display-name="GitHub Actions Pool" \
        --description="Pool for GitHub Actions Workload Identity Federation"
    log_success "Workload Identity Pool created"
fi

# Step 6: Create Workload Identity Provider
echo ""
log_info "Step 6/8: Creating Workload Identity Provider..."
if gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" &>/dev/null; then
    log_warning "Workload Identity Provider already exists, skipping creation"
else
    gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
        --location="global" \
        --workload-identity-pool="$POOL_NAME" \
        --display-name="GitHub Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
        --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
        --issuer-uri="https://token.actions.githubusercontent.com"
    log_success "Workload Identity Provider created"
fi

# Step 7: Configure IAM binding for Workload Identity
echo ""
log_info "Step 7/8: Configuring IAM binding for Workload Identity..."
POOL_ID=$(gcloud iam workload-identity-pools describe "$POOL_NAME" \
    --location="global" \
    --format="value(name)")

gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}" \
    --quiet >/dev/null

log_success "IAM binding configured"

# Step 8: Create Artifact Registry repository
echo ""
log_info "Step 8/8: Creating Artifact Registry repository..."
if gcloud artifacts repositories describe senda \
    --location="$REGION" &>/dev/null; then
    log_warning "Artifact Registry repository already exists"
else
    gcloud artifacts repositories create senda \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for Senda API"
    log_success "Artifact Registry repository created"
fi

# Output GitHub secrets
echo ""
echo "============================================================================"
log_success "Setup complete! Configure these GitHub secrets:"
echo "============================================================================"
echo ""

PROVIDER_FULL_NAME=$(gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" \
    --format="value(name)")

echo -e "${YELLOW}GCP_PROJECT_ID${NC}:"
echo -e "  ${GREEN}${PROJECT_ID}${NC}"
echo ""
echo -e "${YELLOW}WIF_PROVIDER${NC}:"
echo -e "  ${GREEN}${PROVIDER_FULL_NAME}${NC}"
echo ""
echo -e "${YELLOW}WIF_SERVICE_ACCOUNT${NC}:"
echo -e "  ${GREEN}${SERVICE_ACCOUNT_EMAIL}${NC}"
echo ""

echo "============================================================================"
log_info "Next Steps:"
echo "============================================================================"
echo ""
echo "1. Add the above secrets to your GitHub repository:"
echo "   Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "2. Create GitHub environments:"
echo "   Settings → Environments → New environment"
echo "   - Create 'staging' (no protection rules)"
echo "   - Create 'production' (add required reviewers)"
echo ""
echo "3. Deploy Terraform infrastructure:"
echo "   cd terraform"
echo "   cp terraform.tfvars.example terraform.tfvars"
echo "   # Edit terraform.tfvars with your project_id"
echo "   terraform init"
echo "   terraform plan"
echo "   terraform apply"
echo ""
echo "4. Push to develop branch to test staging deployment"
echo ""
echo "============================================================================"
log_success "GCP setup complete!"
echo "============================================================================"
