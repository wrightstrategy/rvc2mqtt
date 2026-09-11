#!/usr/bin/env python3
"""Exercise digest-preserving and immutable promotion against a disposable registry."""
import hashlib
import json
import subprocess
import time
import urllib.request
import uuid

from image_tags import digest, promote

REGISTRY = 'registry:3@sha256:1be55279f18a2fe1a74edf2664cac61c1bea305b7b4642dab412e7affdcb3e33'


def docker(*args, **kwargs):
    result = subprocess.run(['docker', *args], text=True, capture_output=True, timeout=60, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


container = docker('run', '-d', '-p', '127.0.0.1::5000', REGISTRY)
refs = []
try:
    port = json.loads(docker('inspect', container))[0]['NetworkSettings']['Ports']['5000/tcp'][0]['HostPort']
    root = '127.0.0.1:' + port
    image = root + '/test-' + uuid.uuid4().hex
    deadline = time.monotonic() + 20
    while True:
        try:
            urllib.request.urlopen('http://' + root + '/v2/', timeout=1).close()
            break
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)
    def put_fixture(marker):
        # Upload synthetic OCI bytes directly: the client and the Docker daemon
        # need not share localhost (Docker Desktop runs its daemon in a VM).
        repository = image.split('/', 1)[1]
        api = 'http://' + root + '/v2/' + repository
        config = json.dumps({'architecture': 'amd64', 'os': 'linux',
                             'config': {'Labels': {'fixture': marker}},
                             'rootfs': {'type': 'layers', 'diff_ids': []}}).encode()
        config_digest = 'sha256:' + hashlib.sha256(config).hexdigest()
        request = urllib.request.Request(api + '/blobs/uploads/', data=b'', method='POST')
        with urllib.request.urlopen(request, timeout=5) as response:
            location = response.headers['Location']
        assert location.startswith('http://' + root + '/')
        location += ('&' if '?' in location else '?') + 'digest=' + config_digest
        request = urllib.request.Request(location, data=config, method='PUT',
                                         headers={'Content-Type': 'application/octet-stream'})
        urllib.request.urlopen(request, timeout=5).close()
        media = 'application/vnd.oci.image.manifest.v1+json'
        manifest = json.dumps({'schemaVersion': 2, 'mediaType': media,
                               'config': {'mediaType': 'application/vnd.oci.image.config.v1+json',
                                          'digest': config_digest, 'size': len(config)},
                               'layers': []}).encode()
        manifest_digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
        request = urllib.request.Request(api + '/manifests/' + manifest_digest, data=manifest,
                                         method='PUT', headers={'Content-Type': media})
        urllib.request.urlopen(request, timeout=5).close()
        index_media = 'application/vnd.oci.image.index.v1+json'
        index = json.dumps({'schemaVersion': 2, 'mediaType': index_media, 'manifests': [
            {'mediaType': media, 'digest': manifest_digest, 'size': len(manifest),
             'platform': {'architecture': 'amd64', 'os': 'linux'}}]}).encode()
        request = urllib.request.Request(api + '/manifests/' + marker, data=index,
                                         method='PUT', headers={'Content-Type': index_media})
        urllib.request.urlopen(request, timeout=5).close()
        return image + ':' + marker

    refs = [put_fixture(marker) for marker in ('a', 'b')]
    first = image + '@' + digest(refs[0])
    second = image + '@' + digest(refs[1])
    target = image + ':1.0.0'
    promote(first, [target], immutable=True)
    promote(first, [target], immutable=True)  # Idempotent retry.
    assert digest(target) == digest(first)
    try:
        promote(second, [target], immutable=True)
    except RuntimeError as error:
        assert 'immutable' in str(error)
    else:
        raise AssertionError('Immutable version was overwritten')
    assert digest(target) == digest(first)
    try:
        promote(image + '@sha256:' + '0' * 64, [image + ':missing'])
    except RuntimeError:
        pass
    else:
        raise AssertionError('Missing source was accepted')
    print('PASS: real registry promotion preserves digest, is idempotent, and rejects replacement/missing source')
finally:
    subprocess.run(['docker', 'rm', '-f', container], check=False, capture_output=True)
