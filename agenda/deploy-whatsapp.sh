#!/bin/bash
# deploy-whatsapp.sh — Desplega bot WhatsApp en Cloud Run

set -e

PROJECT_ID="solar-dialect-408720"  # Cambia a tu proyecto GCP
SERVICE_NAME="whatsapp-bot"
REGION="us-central1"

echo "🚀 Desplegando WhatsApp bot en Cloud Run..."

# Construir imagen
echo "🔨 Construyendo imagen Docker..."
gcloud builds submit \
  --project=$PROJECT_ID \
  --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --dockerfile=agenda/Dockerfile \
  .

# Desplegar en Cloud Run
echo "📤 Desplegando en Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --project=$PROJECT_ID \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --memory 512Mi \
  --timeout 540

echo "✅ Desplegado. Obtén la URL con:"
echo "gcloud run services describe $SERVICE_NAME --project=$PROJECT_ID --region=$REGION --format='value(status.url)'"
