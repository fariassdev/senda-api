#!/bin/bash
# =============================================================================
# Senda - Database Migration Script
# =============================================================================
# This script runs Alembic migrations for the Senda application.
# It's designed to be executed as a Cloud Run Job before deploying a new
# version of the application.
#
# Usage:
#   ./scripts/run-migrations.sh
#
# Environment Variables Required:
#   - DATABASE_URL or POSTGRES_* variables (configured via get_app_settings)
#
# Exit Codes:
#   0 - Migrations applied successfully
#   1 - Migration failed
# =============================================================================

set -e  # Exit on any error

echo "=========================================="
echo "  Senda Database Migration"
echo "=========================================="
echo ""

# Display current timestamp
echo "📅 Started at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo "❌ Error: alembic command not found"
    exit 1
fi

# Show current migration status
echo "📊 Current migration status:"
alembic -c senda/infrastructure/alembic.ini current
echo ""

# Check for pending migrations
echo "🔍 Checking for pending migrations..."
PENDING=$(alembic -c senda/infrastructure/alembic.ini heads --verbose 2>&1) || true
echo "$PENDING"
echo ""

# Apply migrations
echo "🚀 Applying migrations..."
alembic -c senda/infrastructure/alembic.ini upgrade head

# Verify final state
echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "📊 Final migration status:"
alembic -c senda/infrastructure/alembic.ini current
echo ""
echo "📅 Finished at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=========================================="
