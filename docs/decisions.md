# Decisions

## 2026-09-08: Remove the process-only healthcheck and unused setuptools (PLT-352)

The image and example Compose configuration no longer run `pgrep` as a healthcheck.
The executable was absent from the deployed image, so every probe failed. Installing
it would only duplicate process-existence information already available from Docker;
it would not detect stalled CAN processing or failed MQTT delivery.

The rollout scan also found two fixable HIGH vulnerabilities in setuptools' vendored
build tools (CVE-2026-23949 and CVE-2026-24049). With operator approval, remove unused
setuptools after dependency installation instead of retaining and upgrading build-only
packages in the runtime image. A temporarily mounted, digest-pinned uv performs package
removal and verifies dependency consistency without remaining in the image.

Keep the foreground Python process and existing restart policy. Report container
state honestly, and verify fresh RV state separately from broker connectivity. See
[container monitoring](DOCKER_DEPLOYMENT.md#container-statistics) for the operational
contract. A functional bridge healthcheck is outside this change's scope.
