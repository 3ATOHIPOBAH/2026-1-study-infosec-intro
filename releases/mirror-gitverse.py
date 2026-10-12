"""Copy the seven published GitHub lab releases to the specified GitVerse repo."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import mimetypes
import os
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = 'aarchipov/2026-1-study-infosec-intro'
API = 'https://api.gitverse.ru'
PREFIX = '/repos/' + DESTINATION
PLAN = json.loads((ROOT / 'releases/labs.json').read_text())['releases']


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new and urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            new.remove_header('Authorization')
        return new


OPENER = urllib.request.build_opener(SafeRedirect())


def request(method, path, payload=None, content_type=None, binary=False):
    url = API + path if path.startswith('/') else path
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https':
        raise RuntimeError('An asset download URL is not HTTPS')
    headers = {'Accept': 'application/vnd.gitverse.object+json;version=1'}
    if parsed.netloc == 'api.gitverse.ru':
        headers['Authorization'] = 'Bearer ' + os.environ['GITVERSE_TOKEN']
    if isinstance(payload, dict):
        payload = json.dumps(payload, ensure_ascii=False).encode()
        content_type = 'application/json'
    if content_type:
        headers['Content-Type'] = content_type
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=180) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if method == 'GET' and error.code == 404 and not binary:
            return None
        detail = ''
        try:
            problem = json.loads(error.read(8192))
            problem = problem.get('error', problem)
            if isinstance(problem, dict):
                detail = ': ' + str(problem.get('message', problem.get('code', '')))
            detail = detail.replace(os.environ.get('GITVERSE_TOKEN', '<unset>'), '[redacted]')[:500]
        except (ValueError, AttributeError):
            pass
        raise RuntimeError(f'GitVerse API returned HTTP {error.code} for {method} {parsed.path}{detail}') from None
    return data if binary else json.loads(data)


def run(*args, env=None):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True, env=env)


def gh(*args):
    return run('gh', *args, '--repo', os.environ['GITHUB_REPOSITORY'])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate():
    assert [r['lab'] for r in PLAN] == list(range(2, 9))
    for release in PLAN:
        assert len(release['assets']) == 7
        for asset in release['assets']:
            path = ROOT / asset['path']
            assert path.is_file() and path.stat().st_size == asset['size'], path
            assert sha(path) == asset['sha256'], path


def sync_git(temp):
    # Token is passed only to Git's credential prompt, never stored in the remote URL.
    askpass = temp / 'askpass.py'
    askpass.write_text('#!/usr/bin/env python3\nimport os,sys\nprint("aarchipov" if "username" in sys.argv[1].lower() else os.environ["GITVERSE_TOKEN"])\n')
    askpass.chmod(0o700)
    env = dict(os.environ, GIT_ASKPASS=str(askpass), GIT_TERMINAL_PROMPT='0')
    run('git', 'remote', 'add', 'gitverse', 'https://gitverse.ru/' + DESTINATION + '.git')
    run('git', 'fetch', 'gitverse', 'main', env=env)
    run('git', 'merge-base', '--is-ancestor', 'refs/remotes/gitverse/main', 'HEAD')
    # No force pushes: a changed destination history stops the operation.
    run('git', 'push', 'gitverse', 'HEAD:refs/heads/main', env=env)
    run('git', 'push', 'gitverse', *['refs/tags/' + r['tag'] for r in PLAN], env=env)


def upload(release_id, asset, path):
    boundary = 'gitverse-' + uuid.uuid4().hex
    mime = mimetypes.guess_type(asset['name'])[0] or 'application/octet-stream'
    header = (f'--{boundary}\r\nContent-Disposition: form-data; name="attachment"; filename="{asset["name"]}"\r\nContent-Type: {mime}\r\n\r\n').encode()
    payload = header + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request('POST', PREFIX + f'/releases/{release_id}/assets?name=' + urllib.parse.quote(asset['name']),
            payload, 'multipart/form-data; boundary=' + boundary)


def destination_assets(release, folder):
    assets = []
    for original in release['assets']:
        asset = dict(original)
        if asset['name'].endswith('.html'):
            html_name = asset['name']
            asset['name'] = html_name[:-5] + '_html.zip'
            archive = folder / asset['name']
            entry = zipfile.ZipInfo(html_name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr(entry, (folder / html_name).read_bytes(), compresslevel=9)
            with zipfile.ZipFile(archive) as check:
                assert check.namelist() == [html_name]
                assert hashlib.sha256(check.read(html_name)).hexdigest() == original['sha256']
            asset['size'] = archive.stat().st_size
            asset['sha256'] = sha(archive)
        assets.append(asset)
    return assets


def destination_body(release, source):
    html = next(a for a in release['assets'] if a['name'].endswith('.html'))
    url = 'https://gitverse.ru/' + DESTINATION + '/content/' + release['tag'] + '/' + html['path']
    return source['body'].rstrip() + '\n\n' + (
        'HTML-презентация приложена отдельным ZIP: GitVerse не поддерживает HTML в ассетах релиза. '
        f'[Презентация в HTML в репозитории]({url}).\n')


def mirror():
    if not os.environ.get('GITVERSE_TOKEN'):
        raise RuntimeError('Add a repository Actions secret named GITVERSE_TOKEN, then rerun this workflow.')
    # Check the configured destination before any git writes.
    if not request('GET', PREFIX):
        raise RuntimeError('The configured GitVerse repository was not found')
    with tempfile.TemporaryDirectory(prefix='gitverse-mirror-') as temp:
        temp = Path(temp)
        github = {}
        destination = {}
        for release in PLAN:
            tag = release['tag']
            info = json.loads(gh('release', 'view', tag, '--json', 'name,body,isDraft,isPrerelease,assets,targetCommitish').stdout)
            assert not info['isDraft'], tag
            assert {a['name'] for a in info['assets']} == {a['name'] for a in release['assets']}, tag
            folder = temp / tag
            folder.mkdir()
            gh('release', 'download', tag, '--dir', str(folder))
            for asset in release['assets']:
                assert sha(folder / asset['name']) == asset['sha256'], (tag, asset['name'])
            github[tag] = info
            destination[tag] = destination_assets(release, folder)
        sync_git(temp)
        for release in PLAN:
            tag = release['tag']
            source = github[tag]
            assets_to_copy = destination[tag]
            body = destination_body(release, source)
            lookup = PREFIX + '/releases/tags/' + urllib.parse.quote(tag)
            target = request('GET', lookup)
            if target is None:
                target = request('POST', PREFIX + '/releases', {
                    'tag_name': tag, 'name': source['name'], 'body': body,
                    'target_commitish': run('git', 'rev-parse', tag + '^{commit}').stdout.strip(),
                    'draft': True, 'prerelease': source['isPrerelease'], 'is_authorized_only': False})
            names = {a['name'] for a in target.get('assets', [])}
            expected = {a['name'] for a in assets_to_copy}
            assert not names - expected, f'{tag} has unexpected destination assets'
            for asset in assets_to_copy:
                if asset['name'] not in names:
                    print(f'{tag}: uploading {asset["name"]}', flush=True)
                    upload(target['id'], asset, temp / tag / asset['name'])
            target = request('GET', lookup)
            assets = {a['name']: a for a in target.get('assets', [])}
            assert set(assets) == expected, f'{tag} is missing destination assets'
            for asset in assets_to_copy:
                info = assets[asset['name']]
                assert info['size'] == asset['size'], (tag, asset['name'])
                # GitVerse added a working Public API attachment URL in September 2026.
                download_url = info.get('url') or info['browser_download_url']
                downloaded = request('GET', download_url, binary=True)
                assert hashlib.sha256(downloaded).hexdigest() == asset['sha256'], (tag, asset['name'])
                if asset['name'].endswith('_html.zip'):
                    original = next(a for a in release['assets'] if a['name'].endswith('.html'))
                    with zipfile.ZipFile(io.BytesIO(downloaded)) as archive:
                        assert archive.namelist() == [original['name']]
                        assert hashlib.sha256(archive.read(original['name'])).hexdigest() == original['sha256']
            request('PATCH', PREFIX + f'/releases/{target["id"]}', {
                'name': source['name'], 'body': body, 'draft': False,
                'prerelease': source['isPrerelease'], 'is_authorized_only': False})
            published = request('GET', lookup)
            assert not published['draft'] and published['body'] == body, tag
            print(f'{tag}: copied and verified 7 files', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    validate()
    if args.check_only:
        print('Validated 7 release definitions and all 49 files')
    else:
        mirror()
