#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy-container-app.sh — Deploy the M2LA API Container App
# ---------------------------------------------------------------------------
# Creates or updates the Container App in an existing Container Apps
# Environment. Run this AFTER pushing the container image to ACR.
#
# Required environment variables:
#   RESOURCE_GROUP            — Azure resource group name
#   ENVIRONMENT_NAME          — Platform environment (dev, test, prod)
#   ACR_LOGIN_SERVER          — ACR login server (e.g. acrm2ladev.azurecr.io)
#   IMAGE_TAG                 — Image tag to deploy (e.g. abc1234)
#   UAMI_RESOURCE_ID          — User Assigned Managed Identity resource ID
#   UAMI_CLIENT_ID            — User Assigned Managed Identity client ID
#   APP_INSIGHTS_CONN_STRING  — Application Insights connection string
#   AI_SERVICES_ENDPOINT      — Azure AI Services endpoint for Foundry
#
# Optional:
#   AI_MODEL                  — Model deployment name (default: gpt-4o)
#   CAE_NAME                  — Container Apps Environment name
#                               (default: cae-m2la-${ENVIRONMENT_NAME})
#   APP_NAME                  — Container App name
#                               (default: ca-m2la-api-${ENVIRONMENT_NAME})
#   TARGET_PORT               — Ingress target port (default: 8000)
#   CPU                       — CPU cores (default: 0.5)
#   MEMORY                    — Memory (default: 1Gi)
#   MIN_REPLICAS              — Min replicas (default: 0)
#   MAX_REPLICAS              — Max replicas (default: 10)
# ---------------------------------------------------------------------------
set -euo pipefail

# ---------------------------------------------------------------------------
# Colors & symbols
# ---------------------------------------------------------------------------
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly RESET='\033[0m'

readonly ICON_ROCKET='🚀'
readonly ICON_CHECK='✅'
readonly ICON_WARN='⚠️'
readonly ICON_ERROR='❌'
readonly ICON_PACKAGE='📦'
readonly ICON_GEAR='⚙️'
readonly ICON_GLOBE='🌐'
readonly ICON_LOCK='🔒'
readonly ICON_CHART='📊'
readonly ICON_CLOCK='🕐'
readonly ICON_INFO='ℹ️'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
banner() {
  echo ""
  echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BLUE}${BOLD}  ${ICON_ROCKET}  M2LA API — Container App Deployment${RESET}"
  echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
}

step() {
  echo -e "${CYAN}${BOLD}▸ $1${RESET}"
}

info() {
  echo -e "  ${DIM}${ICON_INFO}  $1${RESET}"
}

success() {
  echo -e "  ${GREEN}${ICON_CHECK}  $1${RESET}"
}

warn() {
  echo -e "  ${YELLOW}${ICON_WARN}  $1${RESET}"
}

fail() {
  echo -e "  ${RED}${ICON_ERROR}  $1${RESET}"
  exit 1
}

divider() {
  echo -e "${DIM}  ──────────────────────────────────────────────────────${RESET}"
}

# ---------------------------------------------------------------------------
# Validate required env vars
# ---------------------------------------------------------------------------
validate_env() {
  step "Validating configuration"

  local missing=0
  for var in RESOURCE_GROUP ENVIRONMENT_NAME ACR_LOGIN_SERVER IMAGE_TAG \
             UAMI_RESOURCE_ID UAMI_CLIENT_ID APP_INSIGHTS_CONN_STRING \
             AI_SERVICES_ENDPOINT; do
    if [[ -z "${!var:-}" ]]; then
      fail "Required variable ${BOLD}${var}${RESET}${RED} is not set"
      missing=1
    fi
  done
  [[ $missing -eq 0 ]] && success "All required variables are set"
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
apply_defaults() {
  CAE_NAME="${CAE_NAME:-cae-m2la-${ENVIRONMENT_NAME}}"
  APP_NAME="${APP_NAME:-ca-m2la-api-${ENVIRONMENT_NAME}}"
  AI_MODEL="${AI_MODEL:-gpt-4o}"
  TARGET_PORT="${TARGET_PORT:-8000}"
  CPU="${CPU:-0.5}"
  MEMORY="${MEMORY:-1Gi}"
  MIN_REPLICAS="${MIN_REPLICAS:-0}"
  MAX_REPLICAS="${MAX_REPLICAS:-10}"
  FULL_IMAGE="${ACR_LOGIN_SERVER}/m2la-api:${IMAGE_TAG}"
}

# ---------------------------------------------------------------------------
# Print deployment summary
# ---------------------------------------------------------------------------
print_summary() {
  step "Deployment plan"
  echo ""
  echo -e "  ${ICON_PACKAGE}  ${BOLD}Image${RESET}         ${FULL_IMAGE}"
  echo -e "  ${ICON_GEAR}  ${BOLD}App${RESET}           ${APP_NAME}"
  echo -e "  ${ICON_GLOBE}  ${BOLD}Environment${RESET}   ${CAE_NAME}"
  echo -e "  ${ICON_LOCK}  ${BOLD}Identity${RESET}      UAMI (${UAMI_CLIENT_ID})"
  echo -e "  ${ICON_CHART}  ${BOLD}Resources${RESET}     ${CPU} vCPU / ${MEMORY}"
  echo -e "  ${ICON_CHART}  ${BOLD}Scale${RESET}         ${MIN_REPLICAS}–${MAX_REPLICAS} replicas"
  echo -e "  ${MAGENTA}${BOLD}     RG${RESET}           ${RESOURCE_GROUP}"
  echo ""
}

# ---------------------------------------------------------------------------
# Check if Container App already exists
# ---------------------------------------------------------------------------
app_exists() {
  az containerapp show \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "name" \
    --output tsv 2>/dev/null && return 0
  return 1
}

# ---------------------------------------------------------------------------
# Create the Container App
# ---------------------------------------------------------------------------
create_app() {
  step "${ICON_ROCKET} Creating Container App"
  info "First deployment — creating ${BOLD}${APP_NAME}${RESET}"

  az containerapp create \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --environment "${CAE_NAME}" \
    --image "${FULL_IMAGE}" \
    --target-port "${TARGET_PORT}" \
    --ingress external \
    --transport auto \
    --cpu "${CPU}" \
    --memory "${MEMORY}" \
    --min-replicas "${MIN_REPLICAS}" \
    --max-replicas "${MAX_REPLICAS}" \
    --scale-rule-name "http-scaling" \
    --scale-rule-type "http" \
    --scale-rule-http-concurrency 50 \
    --user-assigned "${UAMI_RESOURCE_ID}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-identity "${UAMI_RESOURCE_ID}" \
    --env-vars \
      "APPLICATIONINSIGHTS_CONNECTION_STRING=${APP_INSIGHTS_CONN_STRING}" \
      "AZURE_CLIENT_ID=${UAMI_CLIENT_ID}" \
      "AZURE_AI_FOUNDRY_ENDPOINT=${AI_SERVICES_ENDPOINT}" \
      "AZURE_AI_MODEL=${AI_MODEL}" \
      "ENVIRONMENT=${ENVIRONMENT_NAME}" \
    --tags "project=mule2logic" "environment=${ENVIRONMENT_NAME}" "managedBy=script" \
    --output none

  success "Container App created"
}

# ---------------------------------------------------------------------------
# Update an existing Container App
# ---------------------------------------------------------------------------
update_app() {
  step "${ICON_PACKAGE} Updating Container App"
  info "Updating ${BOLD}${APP_NAME}${RESET} → ${DIM}${FULL_IMAGE}${RESET}"

  # Ensure UAMI is assigned (idempotent — no-op if already attached)
  az containerapp identity assign \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --user-assigned "${UAMI_RESOURCE_ID}" \
    --output none

  success "User-assigned managed identity verified"

  # Ensure registry uses UAMI for image pull
  az containerapp registry set \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --server "${ACR_LOGIN_SERVER}" \
    --identity "${UAMI_RESOURCE_ID}" \
    --output none

  success "Registry identity verified"

  az containerapp update \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --image "${FULL_IMAGE}" \
    --set-env-vars \
      "APPLICATIONINSIGHTS_CONNECTION_STRING=${APP_INSIGHTS_CONN_STRING}" \
      "AZURE_CLIENT_ID=${UAMI_CLIENT_ID}" \
      "AZURE_AI_FOUNDRY_ENDPOINT=${AI_SERVICES_ENDPOINT}" \
      "AZURE_AI_MODEL=${AI_MODEL}" \
      "ENVIRONMENT=${ENVIRONMENT_NAME}" \
    --output none

  success "Container App updated"
}

# ---------------------------------------------------------------------------
# Show final status
# ---------------------------------------------------------------------------
show_result() {
  step "Verifying deployment"

  local fqdn
  fqdn=$(az containerapp show \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv 2>/dev/null || echo "")

  local provisioning
  provisioning=$(az containerapp show \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "properties.provisioningState" \
    --output tsv 2>/dev/null || echo "Unknown")

  echo ""
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${GREEN}${BOLD}  ${ICON_CHECK}  Deployment complete${RESET}"
  echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo -e "  ${BOLD}State${RESET}    ${provisioning}"
  if [[ -n "${fqdn}" ]]; then
    echo -e "  ${BOLD}URL${RESET}      ${CYAN}https://${fqdn}${RESET}"
    echo -e "  ${BOLD}Health${RESET}   ${CYAN}https://${fqdn}/health${RESET}"
  fi
  echo -e "  ${BOLD}Image${RESET}    ${FULL_IMAGE}"
  echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  local start_time
  start_time=$(date +%s)

  banner
  validate_env
  apply_defaults
  print_summary
  divider

  if app_exists; then
    update_app
  else
    create_app
  fi

  divider
  show_result

  local end_time elapsed
  end_time=$(date +%s)
  elapsed=$(( end_time - start_time ))
  echo -e "  ${ICON_CLOCK}  Completed in ${BOLD}${elapsed}s${RESET}"
  echo ""
}

main "$@"
