#!/usr/bin/env bash
# GitHub-hosted Linux x64 CI; local developers install the same pinned version.
set -euo pipefail
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
curl --fail --silent --show-error --location \
  https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz \
  --output "$scratch/gitleaks.tar.gz"
printf '%s  %s\n' 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb "$scratch/gitleaks.tar.gz" | sha256sum --check
tar -xzf "$scratch/gitleaks.tar.gz" -C "$scratch" gitleaks
mkdir -p "$HOME/.local/bin"
install -m 755 "$scratch/gitleaks" "$HOME/.local/bin/gitleaks"
echo "$HOME/.local/bin" >> "$GITHUB_PATH"
