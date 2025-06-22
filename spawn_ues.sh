#!/bin/bash
set -e

RELEASE_NAME="ueransim-gnb"
CHART="oci://registry-1.docker.io/gradiant/ueransim-gnb"
VERSION="0.2.6"
NAMESPACE="default"
VALUES_FILE="gnb-ues-values.yaml"
KUBECONFIG_PATH="$HOME/.kube/config-cluster-06-19T19:14:03"



TARGET_COUNT=$1

if [[ -z "$TARGET_COUNT" ]]; then
  echo "Usage: $0 <target_ue_count>"
  exit 1
fi

echo "Scaling UERANSIM UE count to $TARGET_COUNT..."

cp $VALUES_FILE tmp-ues-values.yaml
yq e ".ues.count = $TARGET_COUNT" -i tmp-ues-values.yaml

helm upgrade --kubeconfig="$KUBECONFIG_PATH" --install $RELEASE_NAME $CHART \
  --version $VERSION \
  -n $NAMESPACE \
  -f tmp-ues-values.yaml

echo "UEs scaled to $TARGET_COUNT."

