#!/usr/bin/env bash
set -e

PROJECT_ID="data-to-dirt-f6ef7"
SERVICE_NAME="data-to-dirt"
REGION="us-central1"

echo "=================================================="
echo "  Deploying Data-to-Dirt to Google Cloud Run      "
echo "=================================================="
echo "[+] Project: $PROJECT_ID"
echo "[+] Region:  $REGION"
echo "[+] Service: $SERVICE_NAME"
echo "=================================================="

# Set project
gcloud config set project "$PROJECT_ID"

# Enable necessary Google Cloud APIs
echo "[+] Enabling Cloud Run and Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy directly from source code using Cloud Build
echo "[+] Building container and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated

echo "=================================================="
echo "  [✓] Successfully Deployed to Google Cloud Run!  "
echo "=================================================="
