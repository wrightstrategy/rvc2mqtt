#!/usr/bin/env bash
set -euo pipefail
uv run --locked --only-group runtime python -m unittest tests.test_config tests.test_publishing -v
uv export --locked --only-group runtime --format requirements-txt --output-file /tmp/rvc2mqtt-requirements.txt >/dev/null
# The command in uv's generated header includes its output filename.
diff -u <(tail -n +3 requirements.txt) <(tail -n +3 /tmp/rvc2mqtt-requirements.txt)
test "$(gitleaks version)" = "8.30.1"
gitleaks git --redact --no-banner
