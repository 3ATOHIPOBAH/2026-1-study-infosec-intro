"""Publish seven lab releases from the committed, hash-checked files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'releases/labs.json').read_text())


def run(*args, check=True):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=check)


def gh(*args, check=True):
    return run('gh', *args, '--repo', os.environ['GITHUB_REPOSITORY'], check=check)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = os.environ['GITHUB_SHA']
    # Validate every file before creating the first release.
    for release in MANIFEST['releases']:
        assert len(release['assets']) == 7
        assert len({a['name'] for a in release['assets']}) == 7
        for asset in release['assets']:
            path = ROOT / asset['path']
            assert path.is_file() and path.stat().st_size == asset['size'], path
            assert digest(path) == asset['sha256'], path
    with tempfile.TemporaryDirectory(prefix='lab-release-') as temp:
        temp = Path(temp)
        for release in MANIFEST['releases']:
            tag = release['tag']
            stage = temp / tag
            stage.mkdir()
            files = []
            for asset in release['assets']:
                dest = stage / asset['name']
                shutil.copyfile(ROOT / asset['path'], dest)
                files.append(str(dest))
            notes = stage / 'release-notes.txt'
            notes.write_text(release['notes'])
            existing = gh('release', 'view', tag, '--json', 'isDraft,targetCommitish,assets,url', check=False)
            if existing.returncode == 0:
                info = json.loads(existing.stdout)
                assert info['targetCommitish'] == target, f'{tag} already points to a different commit'
                if info['isDraft']:
                    gh('release', 'upload', tag, *files, '--clobber')
            else:
                gh('release', 'create', tag, *files, '--target', target,
                   '--title', release['title'], '--notes-file', str(notes), '--draft', '--latest=false')
            info = json.loads(gh('release', 'view', tag, '--json', 'isDraft,assets,url').stdout)
            expected = {a['name'] for a in release['assets']}
            assert {a['name'] for a in info['assets']} == expected, f'{tag}: incorrect asset list'
            downloaded = stage / 'download-check'
            downloaded.mkdir()
            gh('release', 'download', tag, '--dir', str(downloaded))
            for asset in release['assets']:
                assert digest(downloaded / asset['name']) == asset['sha256'], f'{tag}: downloaded asset differs'
            if info['isDraft']:
                gh('release', 'edit', tag, '--draft=false', '--latest=false')
            print(f"Published {tag}: {info['url']} (7 verified files)", flush=True)


if __name__ == '__main__':
    main()
