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

## 2026-09-11: Test and scan before image promotion (PLT-260 scope extension)

Scott approved extending the prerequisite to repair its publishing path. The public app
cannot call Bridge's private workflow, so local workflows implement the same binding
artifact contract. Main builds one candidate index with both existing architectures,
provenance and SBOM; tests and vulnerability scans precede commit-tag promotion. Releases
promote that exact index and never rebuild. Existing full-version tags cannot be overwritten.

A locked runtime dependency group preserves the current dependency versions without making
these scripts a Python package. A dispatched, pinned python-semantic-release tool creates
stable tags with the existing organization App token, without a release commit. Deployment
steps and image identity are carried in release notes. `latest` now tracks stable releases;
`edge` carries verified main builds. See [releasing](RELEASING.md) for the current contract,
verification coverage, inherited legacy-test limitations, and operator actions.

## 2026-09-13: Patch the base image in the build, not only by digest (SWW-201)

Twelve fixable HIGH/CRITICAL Debian advisories (perl-base, libpcre2-8-0, libsqlite3-0,
gzip) landed after Docker last rebuilt `python:3.11-slim`. The pinned digest was already
the current upstream tag, so there was no refreshed base to bump to and the required
`pr / verify` check blocked every pull request. Apply Debian security updates in the
`base` stage instead of waiting on upstream's rebuild cadence, keeping the digest pin for
build provenance. Scan policy is unchanged: the gate still fails on fixable HIGH/CRITICAL,
which is what makes these advisories actionable rather than allowlistable.

This trades exact build reproducibility for timely patching. Build-once-then-promote
already means one scanned digest per commit, so the promoted artifact is still exactly
what CI tested. See [releasing](RELEASING.md).
