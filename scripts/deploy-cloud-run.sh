#!/bin/sh
set -eu
PROJECT_ID=casemind-ai
REGION=asia-southeast1
REPOSITORY=casemind-prototype
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/workspace:prototype"
PROCESSOR=$(python3 -c 'import json; print(json.load(open("artifacts/cloud-config.json"))["processor"])')
if ! gcloud --configuration=casemind-ai artifacts repositories describe "$REPOSITORY" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud --configuration=casemind-ai artifacts repositories create "$REPOSITORY" --repository-format=docker --location="$REGION" --project="$PROJECT_ID" --quiet
fi
gcloud --configuration=casemind-ai builds submit --project="$PROJECT_ID" --region="$REGION" --tag="$IMAGE" --timeout=900s --quiet
gcloud --configuration=casemind-ai run deploy casemind-ai --project="$PROJECT_ID" --region="$REGION" --image="$IMAGE" \
  --service-account="casemind-runtime@${PROJECT_ID}.iam.gserviceaccount.com" \
  --cpu=1 --memory=512Mi --concurrency=4 --min-instances=0 --max-instances=1 --max=1 --timeout=150s \
  --no-cpu-boost --allow-unauthenticated \
  --set-env-vars="CASEMIND_CLOUD=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CASEMIND_REGION=${REGION},CASEMIND_BUCKET=casemind-ai-prototype-251896792352,CASEMIND_PROCESSOR=${PROCESSOR}" --quiet
