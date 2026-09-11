#!/usr/bin/env python3
"""Promote an existing image digest, preserving its index and attestations."""
import argparse
import json
import re
import subprocess


def digest(reference, *, missing_ok=False):
    result = subprocess.run(
        ['docker', 'buildx', 'imagetools', 'inspect', reference, '--format', '{{json .Manifest}}'],
        text=True, capture_output=True,
    )
    if result.returncode:
        if missing_ok and ('not found' in result.stderr.lower() or 'manifest unknown' in result.stderr.lower()):
            return None
        raise RuntimeError('Cannot inspect image reference: ' + reference)
    value = json.loads(result.stdout)['digest']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise RuntimeError('Registry returned an invalid digest')
    return value


def promote(source, tags, *, immutable=False):
    expected = source.rsplit('@', 1)[-1]
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', expected) or digest(source) != expected:
        raise ValueError('Promotion requires an existing exact image digest')
    for tag in tags:
        existing = digest(tag, missing_ok=True)
        if existing == expected:
            continue
        if immutable and existing is not None:
            raise RuntimeError('Refusing to replace an existing immutable tag: ' + tag)
        subprocess.run(['docker', 'buildx', 'imagetools', 'create', '--prefer-index=false',
                        '--tag', tag, source], check=True)
        if digest(tag) != expected:
            raise RuntimeError('Promoted tag does not match the source digest: ' + tag)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--immutable', action='store_true')
    parser.add_argument('source')
    parser.add_argument('tags', nargs='+')
    args = parser.parse_args()
    promote(args.source, args.tags, immutable=args.immutable)
