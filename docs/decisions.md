# Decisions

## 2026-09-08: Remove the process-only Docker healthcheck (PLT-352)

The image and example Compose configuration no longer run `pgrep` as a healthcheck.
The executable was absent from the deployed image, so every probe failed. Installing
it would only duplicate process-existence information already available from Docker;
it would not detect stalled CAN processing or failed MQTT delivery.

Keep the foreground Python process and existing restart policy. Report container
state honestly, and verify fresh RV state separately from broker connectivity. See
[container monitoring](DOCKER_DEPLOYMENT.md#container-statistics) for the operational
contract. A functional bridge healthcheck is outside this change's scope.
