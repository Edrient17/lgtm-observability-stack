#!/usr/bin/env bash
set -euo pipefail

namespace="${K3S_NAMESPACE:-msa-demo}"

usage() {
  cat <<EOF
Usage: $0 <action>

Actions:
  api-down | api-up
  catalog-down | catalog-up
  inventory-down | inventory-up
  cart-down | cart-up
  order-down | order-up
  payment-down | payment-up
  node-exporter-down | node-exporter-up
  alloy-down | alloy-up
  recover-all
EOF
}

scale_deployment() {
  local name="$1"
  local replicas="$2"
  kubectl -n "${namespace}" scale deployment "${name}" --replicas="${replicas}"
}

delete_daemonset() {
  local name="$1"
  kubectl -n "${namespace}" delete daemonset "${name}" --ignore-not-found
}

restore_resource() {
  local file="$1"
  kubectl apply -f "${file}"
}

action="${1:-}"
case "${action}" in
  api-down) scale_deployment api-service 0 ;;
  api-up) scale_deployment api-service 1 ;;
  catalog-down) scale_deployment catalog-service 0 ;;
  catalog-up) scale_deployment catalog-service 1 ;;
  inventory-down) scale_deployment inventory-service 0 ;;
  inventory-up) scale_deployment inventory-service 1 ;;
  cart-down) scale_deployment cart-service 0 ;;
  cart-up) scale_deployment cart-service 1 ;;
  order-down) scale_deployment order-service 0 ;;
  order-up) scale_deployment order-service 1 ;;
  payment-down) scale_deployment payment-service 0 ;;
  payment-up) scale_deployment payment-service 1 ;;
  node-exporter-down) delete_daemonset node-exporter ;;
  node-exporter-up) restore_resource k3s/app-vm/node-exporter.yaml ;;
  alloy-down) delete_daemonset alloy ;;
  alloy-up) restore_resource k3s/app-vm/alloy.yaml ;;
  recover-all)
    for deployment in api-service catalog-service inventory-service cart-service order-service payment-service; do
      scale_deployment "${deployment}" 1
    done
    restore_resource k3s/app-vm/node-exporter.yaml
    restore_resource k3s/app-vm/alloy.yaml
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "Unknown action: ${action}" >&2
    usage
    exit 1
    ;;
esac
