#!/usr/bin/env python3
"""
Upload the combined EasyBuild module list to a MediaWiki instance.

Only the single page configured in ~/.config/mediawiki/bwhpc.conf is touched.
No pages are deleted.  The edit uses action=edit which updates an existing
page or creates it if it does not yet exist.

Configuration file: ~/.config/mediawiki/bwhpc.conf  (INI format)

    [mediawiki]
    url      = https://wiki.bwhpc.de/e        ; article base URL (for reference)
    api      = https://wiki.bwhpc.de/w/api.php  ; API endpoint (optional — auto-discovered via wgScriptPath)
    page     = NEMO2/Modules                 ; target wiki page
    file     = wiki/Easybuild_Module_List.mediawiki  ; local source file
    username = YourMainUsername@BotName      ; bot user (user@botname)
    password = theActualBotPassword          ; bot password
    summary  = Auto-update: EasyBuild module list    ; optional edit summary

The credentials are never printed or logged.
"""

import configparser
import http.cookiejar
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error

DEFAULT_CONFIG = os.path.expanduser('~/.config/mediawiki/bwhpc.conf')
DEFAULT_SUMMARY = 'Auto-update: EasyBuild module list (bot)'


# ---------------------------------------------------------------------------
# API endpoint discovery
# ---------------------------------------------------------------------------

def _discover_api(article_base_url: str) -> str:
    """
    Try to discover the MediaWiki API endpoint by reading wgScriptPath from
    any wiki page's HTML.  Falls back to article_base_url/api.php on failure.
    """
    try:
        req = urllib.request.Request(article_base_url)
        req.add_header('User-Agent', 'EasyBuildModuleUploader/1.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'"wgScriptPath"\s*:\s*"([^"]*)"', html)
        if m:
            script_path = m.group(1)            # e.g. "" or "/w" or "/wiki"
            parsed = urllib.parse.urlparse(article_base_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            discovered = base + script_path + '/api.php'
            print(f"[info] Discovered API endpoint via wgScriptPath: {discovered}")
            return discovered
    except Exception as exc:
        print(f"[warn] API auto-discovery failed: {exc}")
    return article_base_url.rstrip('/') + '/api.php'


def _verify_api(api_url: str) -> bool:
    """Return True if api_url responds with a valid MediaWiki API JSON response."""
    try:
        url = api_url + '?' + urllib.parse.urlencode({
            'action': 'query', 'meta': 'siteinfo', 'format': 'json'})
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'EasyBuildModuleUploader/1.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return 'query' in data or 'error' in data
    except Exception:
        return False


# ---------------------------------------------------------------------------
# HTTP helpers (no third-party deps)
# ---------------------------------------------------------------------------

def _make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _api_call(opener: urllib.request.OpenerDirector, api_url: str,
              params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(api_url, data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('User-Agent', 'EasyBuildModuleUploader/1.0')
    with opener.open(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _api_get(opener: urllib.request.OpenerDirector, api_url: str,
             params: dict) -> dict:
    url = api_url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'EasyBuildModuleUploader/1.0')
    with opener.open(req) as resp:
        return json.loads(resp.read().decode('utf-8'))


# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------

def upload(cfg: configparser.SectionProxy) -> bool:
    api = cfg['url'].rstrip('/') + '/api.php'
    if cfg.get('api'):
        api = cfg['api'].rstrip('/')
    else:
        api = _discover_api(cfg['url'])

    if not _verify_api(api):
        print(f"Error: API endpoint not reachable or not a valid MediaWiki API: {api}")
        print("Set the 'api' key in your config to the correct URL, e.g.:")
        print("  api = https://wiki.bwhpc.de/w/api.php")
        return False

    opener = _make_opener()

    # 1. Fetch login token
    resp = _api_get(opener, api, {
        'action': 'query',
        'meta':   'tokens',
        'type':   'login',
        'format': 'json',
    })
    login_token = resp['query']['tokens']['logintoken']

    # 2. Login with bot password (action=login accepts user@botname format)
    resp = _api_call(opener, api, {
        'action':     'login',
        'lgname':     cfg['username'],
        'lgpassword': cfg['password'],
        'lgtoken':    login_token,
        'format':     'json',
    })
    login_result = resp.get('login', {}).get('result')
    if login_result != 'Success':
        print(f"Login failed: {resp.get('login', {}).get('reason', resp)}")
        return False
    print(f"Logged in as {resp['login'].get('lgusername', cfg['username'])}")

    # 3. Fetch CSRF token
    resp = _api_get(opener, api, {
        'action': 'query',
        'meta':   'tokens',
        'format': 'json',
    })
    csrf = resp['query']['tokens']['csrftoken']

    # 4. Read local file
    src = cfg.get('file', 'wiki/Easybuild_Module_List.mediawiki')
    if not os.path.isfile(src):
        print(f"Source file not found: {src}")
        print("Run 'make wiki' first to generate it.")
        return False
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    summary = cfg.get('summary', DEFAULT_SUMMARY)
    page    = cfg['page']

    # 5. Edit the page (creates if absent, updates if present — never deletes)
    resp = _api_call(opener, api, {
        'action':  'edit',
        'title':   page,
        'text':    content,
        'summary': summary,
        'token':   csrf,
        'format':  'json',
        'bot':     '1',
    })
    edit = resp.get('edit', {})
    result = edit.get('result')
    if result == 'Success':
        if 'nochange' in edit:
            print(f"Page '{page}': already up to date, no change made.")
        else:
            rev = edit.get('newrevid', '?')
            print(f"Page '{page}' updated successfully (rev {rev}).")
        return True

    print(f"Edit failed: {resp}")
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description='Upload EasyBuild module list to MediaWiki')
    parser.add_argument('--config', '-c', default=DEFAULT_CONFIG,
                        help=f'Config file (default: ~/.config/mediawiki/bwhpc.conf)')
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"Config file not found: {args.config}")
        print("Copy .config/mediawiki.conf.example to ~/.config/mediawiki/bwhpc.conf")
        print("and fill in your credentials.")
        return 1

    cfg = configparser.ConfigParser()
    cfg.read(args.config, encoding='utf-8')

    if 'mediawiki' not in cfg:
        print(f"Missing [mediawiki] section in {args.config}")
        return 1

    section = cfg['mediawiki']
    for required in ('url', 'page', 'username', 'password'):
        if not section.get(required):
            print(f"Missing required key '{required}' in {args.config}")
            return 1

    return 0 if upload(section) else 1


if __name__ == '__main__':
    sys.exit(main())
