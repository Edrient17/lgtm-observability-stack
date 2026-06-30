# Troubleshooting

Use this file as a live build log. The final report requires at least two real troubleshooting cases.

## Case 1: Mimir or Tempo Cannot Access MinIO Bucket

- Symptom:
  - Mimir or Tempo starts but logs S3 bucket or access denied errors.
- Likely cause:
  - `minio-init` did not complete, credentials differ from `.env`, or a service started before bucket creation.
- Fix:
  - Check `docker compose logs minio-init`.
  - Confirm `.env` values match `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`.
  - Run `docker compose up -d minio-init`.
  - Restart the failing service.

## Case 2: Grafana Dashboard Has No Data

- Symptom:
  - Dashboards load but panels show `No data`.
- Likely cause:
  - Sample traffic has not been generated yet, Prometheus targets are down, or Mimir remote write is not ready.
- Fix:
  - Run `./scripts/generate-load.sh`.
  - Check Prometheus targets at `http://localhost:9090/targets`.
  - Query `up` in Grafana Explore using the Mimir datasource.

## Case 3: Promtail Does Not Collect Docker Logs

- Symptom:
  - Loki works, but `{job="docker"}` returns no streams.
- Likely cause:
  - The deployment host is not Linux Docker Engine, or `/var/lib/docker/containers` is unavailable.
- Fix:
  - Deploy on the target Ubuntu VM.
  - Confirm Docker JSON log files exist under `/var/lib/docker/containers`.
  - Restart Promtail after containers generate new logs.

## Case 4: Docker Permission Denied

- Symptom:
  - `docker compose up -d --build` or `docker info` fails with a Docker socket permission error.
- Likely cause:
  - The current VM user is not a member of the `docker` group.
- Fix:
  - Run `sudo usermod -aG docker $USER`.
  - Run `newgrp docker`, or log out of SSH and log back in.
  - Confirm with `docker info`.

## Case 5: Docker Container Log Path Is Missing

- Symptom:
  - Promtail fails to start or Docker log scraping does not work because `/var/lib/docker/containers` is unavailable.
- Likely cause:
  - Docker is installed with a non-default data root, or the current user cannot inspect the directory directly.
- Fix:
  - Check Docker's root directory with `docker info --format '{{.DockerRootDir}}'`.
  - Confirm container logs exist under that directory after containers have started.
  - If the root directory is not `/var/lib/docker`, update the Promtail bind mount in `docker-compose.yml` before restarting Promtail.
