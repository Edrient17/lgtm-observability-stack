#!/usr/bin/env bash
set -euo pipefail

image_name="${MSA_DEMO_IMAGE:-msa-demo:local}"
archive_path="${MSA_DEMO_IMAGE_ARCHIVE:-/tmp/msa-demo-local.tar}"

echo "Building ${image_name} from ./msa-demo"
docker build -t "${image_name}" ./msa-demo

echo "Saving ${image_name} to ${archive_path}"
docker save "${image_name}" -o "${archive_path}"

echo "Importing ${archive_path} into k3s containerd"
sudo k3s ctr images import "${archive_path}"

echo "Loaded ${image_name} into k3s"
