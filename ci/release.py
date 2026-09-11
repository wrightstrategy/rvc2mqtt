#!/usr/bin/env python3
"""Cut a stable, tag-only release from a verified main image; never build an image."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from image_tags import digest, promote

PSR = ['uvx', '--from', 'python-semantic-release==10.6.2', 'semantic-release', 'version']
TAG = re.compile(r'v(\d+)\.(\d+)\.(\d+)')


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=True).stdout.strip()


def release_notes(messages, deploy_steps, image, sha):
    entries = []
    for message in messages:
        lines = message.strip().splitlines()
        if not lines:
            continue
        match = re.fullmatch(r'(\w+)(?:\([^)]*\))?(!)?: (.+)', lines[0])
        breaking = 'BREAKING CHANGE:' in message or 'BREAKING-CHANGE:' in message
        if match and (match[1] in ('fix', 'feat') or match[2] or breaking):
            entries.append('- ' + lines[0])
            if match[2] or breaking:
                entries.extend('  ' + line for line in lines[1:] if line.strip())
    return (deploy_steps.rstrip() + '\n\n## Changes\n\n' + '\n'.join(entries)
            + f'\n\n## Image\n\n`{image}`\n\nSource commit: `{sha}`\n')


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    sha = os.environ['GITHUB_SHA']
    if os.environ['GITHUB_REF'] != 'refs/heads/main' or run('git', 'rev-parse', 'HEAD') != sha:
        raise RuntimeError('Release must use the selected main commit')
    tip = json.loads(run('gh', 'api', f'repos/{repo}/commits/main'))['sha']
    if tip != sha:
        raise RuntimeError('Main advanced since dispatch; dispatch again on its current commit')
    runs = json.loads(run('gh', 'api', f'repos/{repo}/actions/workflows/docker-build.yml/runs?event=push&head_sha={sha}&status=success'))
    if not any(item['head_sha'] == sha and item['head_branch'] == 'main' and item['conclusion'] == 'success'
               for item in runs['workflow_runs']):
        raise RuntimeError('No successful main image workflow for this exact commit')
    image = 'ghcr.io/' + repo.lower()
    source = image + '@' + digest(image + ':sha-' + sha)
    existing = [tag for tag in run('git', 'tag', '--points-at', 'HEAD').splitlines() if TAG.fullmatch(tag)]
    if len(existing) > 1:
        raise RuntimeError('Multiple stable tags on this commit; resolve release identity first')
    bump = os.environ.get('RELEASE_BUMP', 'auto')
    if bump not in ('auto', 'minor', 'major'):
        raise ValueError('Invalid bump')
    flags = [] if bump == 'auto' else ['--' + bump]
    tag = existing[0] if existing else run(*PSR, '--print-tag', *flags)
    match = TAG.fullmatch(tag)
    if not match:
        raise RuntimeError('Expected a stable semantic version')
    # Last reachable release before this commit: retrying a partial release has
    # exactly the same notes and does not calculate another version on the same SHA.
    previous = subprocess.run(['git', 'describe', '--tags', '--match', 'v[0-9]*', '--abbrev=0', 'HEAD^'],
                              text=True, capture_output=True)
    revision_range = previous.stdout.strip() + '..HEAD' if previous.returncode == 0 else 'HEAD'
    messages = run('git', 'log', '--format=%B%x00', revision_range).split('\x00')
    notes = release_notes(messages, Path('deploy/deploy_next.md').read_text(), source, sha)
    print(f'Release {tag} from {source}\n{notes}')
    if os.environ.get('RELEASE_DRY_RUN', 'true') == 'true':
        return
    if not existing:
        run(*PSR, '--no-commit', '--no-changelog', '--skip-build', '--push', '--no-vcs-release', *flags)
    if run('git', 'rev-parse', tag + '^{commit}') != sha:
        raise RuntimeError('Release tag does not point to the verified commit')
    promote(source, [image + ':' + tag[1:]], immutable=True)
    promote(source, [image + ':' + match[1] + '.' + match[2], image + ':latest'])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'notes.md'
        path.write_text(notes)
        releases = json.loads(run('gh', 'api', f'repos/{repo}/releases?per_page=100'))
        exists = any(release['tag_name'] == tag for release in releases)
        if exists:
            run('gh', 'release', 'edit', tag, '--repo', repo, '--notes-file', str(path))
        else:
            run('gh', 'release', 'create', tag, '--repo', repo, '--verify-tag', '--title', tag,
                '--notes-file', str(path), '--latest')


if __name__ == '__main__':
    main()
