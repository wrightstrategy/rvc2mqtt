# Pending deployment steps

## Remove the obsolete container healthcheck (PLT-352, PR #26)

- When: with the new image.
- Tiers: existing Docker/Compose installations, including rv-server.
- Progress: rv-server completed on 2026-09-08 via homelab PR #2062; verified running
  without a healthcheck and publishing fresh RV state. The steps below still apply
  to other existing installations.
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

## Require external MQTT configuration (PLT-260)

- When: before upgrading to this image.
- Tiers: all Docker/Compose installations; homelab rv-server.
- Do: provision a complete external `rvc2mqtt.ini`, preserving the existing deployment's
  CAN, discovery, commands, rate limits, security, and audit settings. Supply broker
  credentials from the deployment secret manager. Mount the file read-only at
  `/app/rvc2mqtt.ini`, readable by UID 99. Set `[MQTT] mqttPort` when using a port
  other than 1883. Remove ineffective `MQTT_*` environment overrides. For a new
  deployment copy the example; do not replace an existing site's complete settings
  with the example's defaults.
- Verify: the image fails without the file; startup reports the declared broker host
  and port; authenticated MQTT connectivity and fresh RV telemetry succeed.
- Why: **breaking deployment change** — images no longer bundle site configuration.
  rv-server must receive the managed mount and verified image digest together through
  homelab PLT-260. Roll back the previous image/configuration pair if cutover fails.
  Removing the new image's configuration does not erase credentials from older artifacts.
