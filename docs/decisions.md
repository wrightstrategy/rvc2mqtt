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

## 2026-09-11: Deployment-owned INI and configurable MQTT port (PLT-260)

Require the deployment to supply the complete INI and read the MQTT port from it
(defaulting to 1883 for existing external files). The old image bundled one site's
connection settings, and its hard-coded port made declarative deployment settings
ineffective. Keeping one INI interface avoids competing environment precedence.
The loader reports configuration failures without echoing credential-bearing input.

See [configuration](../README.md#configuration) and the pending deployment steps.
Non-broker behavior and the existing INI dialect are preserved. Historical images
and repository history are not rewritten; historical credential exposure is a
separate operator decision.
