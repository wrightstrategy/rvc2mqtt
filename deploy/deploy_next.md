# Pending deployment steps

## Remove the obsolete container healthcheck (PLT-352, PR #26)

- When: with the new image.
- Tiers: existing Docker/Compose installations, including rv-server.
- Do: remove deployment-level copies of the `pgrep` healthcheck and recreate the
  container using the new image. For the example Compose deployment, use the updated
  `docker-compose.yml`, then `docker compose pull && docker compose up -d`.
  rv-server is managed by homelab's NixOS configuration: replace its old
  `ghcr.io/wrightbuilt/rvc2mqtt` pin with the verified
  `ghcr.io/wrightstrategy/rvc2mqtt` image digest through the homelab deployment
  workflow. Before that cutover, verify registry pull access and compatibility with
  the existing application configuration and mappings.
- Verify: `docker inspect rvc2mqtt --format '{{json (index .State "Health")}}'` returns `null`,
  the container remains running, and fresh RV state updates still reach Home
  Assistant. Check the separate MQTT prober as broker-path evidence only.
- Why: the old process probe cannot pass and does not measure bridge functionality;
  changing this repository alone does not update existing containers or image pins.
