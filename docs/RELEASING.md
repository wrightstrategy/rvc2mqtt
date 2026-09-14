# Building and releasing

`Image CI` runs on every PR and main push. Public and fork code runs on GitHub-hosted
Ubuntu; this public repo cannot access the organization's private runner pool or call
Bridge's private reusable workflows. The local `image-check.yml` owns the same build,
scan, and promotion contract. It consumes no private source or fork-accessible credentials.

`pyproject.toml`'s `runtime` dependency group and `uv.lock` own runtime dependencies.
This is a collection of scripts, not an installed Python package. `.python-version`
selects the tested Python 3.11 runtime. `requirements.txt` is generated with:

```sh
uv export --locked --only-group runtime --format requirements-txt --output-file requirements.txt
```

The runtime dependency versions were preserved when introducing the lock. Docker uses
an isolated virtual environment, retains UID 99:100, and removes the unused system
setuptools as before. Version identity comes from git release tags and the image digest;
the old hard-coded `2.5.0` Docker label was removed. There were no existing `v*` git tags
at adoption; the first formal stable release is derived from history, starting at 1.0.0.

## Checks and local work

Install uv 0.12.11 and gitleaks 8.30.1, then enable the committed pre-commit hook with
`git config core.hooksPath .githooks`. If another hook is already configured, retain it
and chain this scanner into it. Run:

```sh
bash ci/check.sh
python3 ci/test-image-promotion.py
docker build -t rvc2mqtt:check .
python3 ci/test-container-config.py rvc2mqtt:check
```

The check runs configuration tests, real-git semantic-release tests, requirements export
consistency, and a full-history redacted gitleaks scan. The registry test uses only an
owned disposable local registry and synthetic images. The application test authenticates
to a disposable MQTT broker on port 2883 and verifies missing external configuration fails.
CI additionally scans the built image with Trivy 0.74.0, failing on fixable HIGH/CRITICAL
vulnerabilities. The adoption full-history gitleaks scan found zero scanner findings;
this does not establish that historical site credentials have been revoked or erased.

The image pins its base by digest and then applies Debian security updates in the same
build (`apt-get upgrade` in the `base` stage). The digest fixes what upstream shipped;
the upgrade covers what Debian has fixed since that upstream rebuild. Without it, a
security advisory published between upstream rebuilds fails the scan gate and blocks
every pull request, with no newer digest available to move to. Every build therefore
carries the security suite as of its own build time, so two builds of the same commit
can differ in OS package versions; the promoted digest is always the one CI scanned.

The unrelated legacy `run_tests.py` suite had 38 failures and 2 errors in 90 tests on
untouched main; its separate core suite had 3 failures. They remain outside this pipeline's
configuration/release acceptance coverage. No CAN encoding or validator behavior was
changed to make these gates pass.

Actionlint 1.7.12 does not recognize GitHub's `concurrency.queue` field; locally ignore only
that unsupported-key diagnostic. The actual release concurrency retains queued dispatches
and never cancels an active publication. Zizmor's medium/high checks apply without exemptions.

## Image identity

- PR: test and build/load amd64, run the real application test, scan; never log into GHCR
  or publish. The PR context to require in branch protection is `pr / verify`.
- Main: build amd64 and arm64 once by digest with maximum provenance and SBOM attestations.
  Run the real application test on amd64 (rv-server's architecture), scan both architectures,
  then attach immutable `sha-<full-commit>` and rolling `edge` tags. Failed candidates receive
  no usable commit/release tag. An existing commit tag cannot be replaced with other bytes.
  Only a build still matching main's current tip updates `edge`; deployments pin digests.
- Release: require a successful `Image CI` main run and the exact commit's existing image.
  There is no build fallback. `X.Y.Z` is immutable; `X.Y` and `latest` move to this stable
  release. Tag promotion verifies the resulting digest equals the source digest, preserving
  its complete index and attestations. Release workflows contain no build step.

The former main-push updates to `latest` and `main` are retired. `latest` now means stable
release; use `edge` deliberately for main builds. The existing amd64/arm64 published
platforms are preserved. This task does not add prerelease or maintenance-branch trains.

## Cut a stable release

Merge only after independent review and required CI. Wait for the main `Image CI` run to
succeed. Dispatch `Cut release` on main with `dry_run=true` (default), then inspect its
computed version, deployment steps, source commit, and existing image digest. The workflow
rejects a selected commit if main advanced before it starts; dispatch again in that case.

After the human release decision, dispatch with `dry_run=false`. `bump=auto` follows
Conventional Commits; `minor` and `major` are explicit alternatives. The pinned
python-semantic-release 10.6.2 tags without changing files or creating a release commit.
It uses the existing organization `BOT_APP_PRIVATE_KEY` to mint a short-lived token scoped
to this repo, with contents-write/actions-read only; the job revokes it on completion.
GHCR uses the workflow's packages-write token. PR jobs receive neither credential.

Only this workflow creates release tags. A partially completed release is retried on the
same current main commit: an existing stable tag on that commit is reused, the same image
is promoted, and its release notes are reconciled. Never move a tag or rebuild to repair a
failed promotion. If main has advanced, stop and inspect the existing tag/image/release
before proceeding; an old failed release is not permission to overwrite newer stable tags.

Release notes lead with `deploy/deploy_next.md`, include fixes/features and breaking
instructions, and end with the exact image index digest and source SHA. Publishing does
not activate rv-server. PLT-260 requires the verified new digest and managed INI mount in
one homelab cutover, followed by authenticated broker and fresh RV telemetry verification.
