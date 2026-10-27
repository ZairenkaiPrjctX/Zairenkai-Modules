#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pin only published, immutable, manifest-verified artifacts for exact source commits."""
from __future__ import annotations
import hashlib, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SHA1=re.compile(r'^[0-9a-f]{40}$'); SHA256=re.compile(r'^[0-9a-f]{64}$')
UA='Zairenkai-Artifact-Pin-Sync/1.0'

def get(url: str) -> bytes:
    headers={'User-Agent':UA,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token and urllib.parse.urlsplit(url).hostname=='api.github.com': headers['Authorization']='Bearer '+token
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as r: return r.read(1_000_000_000+1)
    except (urllib.error.URLError,TimeoutError) as e: raise RuntimeError(f'GET {url}: {e}') from e

def jsonobj(data: bytes,label: str)->dict:
    try: x=json.loads(data)
    except (ValueError,UnicodeDecodeError) as e: raise RuntimeError(f'{label}: invalid JSON: {e}') from e
    if not isinstance(x,dict): raise RuntimeError(f'{label}: expected JSON object')
    return x

def published_pin(repo: str, component: str, commit: str) -> dict|None:
    if not SHA1.fullmatch(commit): raise RuntimeError(f'{repo}: source commit is not full SHA-1')
    tag='artifact-'+commit
    url=f'https://api.github.com/repos/{repo}/releases/tags/{tag}'
    try: release=jsonobj(get(url),f'{repo}/{tag} release')
    except RuntimeError as e:
        if 'HTTP Error 404' in str(e) or '404' in str(e): return None
        raise
    if release.get('tag_name')!=tag or release.get('draft') is True or release.get('prerelease') is True:
        return None
    byname={a.get('name'):a for a in release.get('assets',[]) if isinstance(a,dict)}
    if len(byname)!=len(release.get('assets',[])): raise RuntimeError(f'{repo}/{tag}: duplicate/invalid asset names')
    if 'artifact-manifest.json' not in byname: return None
    raw=get(byname['artifact-manifest.json'].get('browser_download_url',''))
    manifest=jsonobj(raw,f'{repo}/{tag} manifest')
    if manifest.get('schema_version')!=1 or manifest.get('repository')!=repo or manifest.get('component')!=component or manifest.get('source_commit')!=commit:
        raise RuntimeError(f'{repo}/{tag}: manifest repository/component/commit mismatch')
    assets=manifest.get('assets')
    if not isinstance(assets,list) or len(assets)!=1: raise RuntimeError(f'{repo}/{tag}: invalid manifest asset list')
    a=assets[0]
    name=a.get('name')
    if not isinstance(name,str) or name not in byname: raise RuntimeError(f'{repo}/{tag}: archive not uploaded')
    gh_asset=byname[name]
    if a.get('size_bytes')!=gh_asset.get('size') or not SHA256.fullmatch(str(a.get('sha256',''))):
        raise RuntimeError(f'{repo}/{tag}: archive metadata/sha256 invalid')
    archive=get(gh_asset.get('browser_download_url',''))
    if len(archive)!=a['size_bytes'] or hashlib.sha256(archive).hexdigest()!=a['sha256']:
        raise RuntimeError(f'{repo}/{tag}: archive size/SHA-256 does not match published manifest')
    manifest_digest=hashlib.sha256(raw).hexdigest()
    if len(raw)!=byname['artifact-manifest.json'].get('size') or not SHA256.fullmatch(manifest_digest):
        raise RuntimeError(f'{repo}/{tag}: manifest download size/hash invalid')
    files=manifest.get('files')
    if not isinstance(files,list) or not files: raise RuntimeError(f'{repo}/{tag}: manifest file list empty')
    return {'repository':repo,'component':component,'source_commit':commit,'release_tag':tag,
            'asset_name':name,'asset_sha256':a['sha256'],'asset_size_bytes':a['size_bytes'],
            'manifest_name':'artifact-manifest.json','manifest_sha256':manifest_digest}

def sync_modules(repo_root: Path)->bool:
    p=repo_root/'components.lock.json'; lock=json.loads(p.read_text())
    changed=False
    for row in lock.get('components',[]):
        repo=row['repository']; component=row['name']; commit=row['commit']
        pin=published_pin(repo,component,commit)
        if pin is None:
            if row.get('release_artifact',{}).get('source_commit')!=commit and 'release_artifact' in row:
                del row['release_artifact']; changed=True
            print(f'{component}: '+('no published verified artifact; source-build fallback remains' if 'release_artifact' not in row else 'retained pinned artifact for same commit'))
            continue
        if row.get('release_artifact')!=pin: row['release_artifact']=pin; changed=True
        print(f'{component}: pinned {pin["release_tag"]} sha256={pin["asset_sha256"]}')
    if changed: p.write_text(json.dumps(lock,indent=2,ensure_ascii=False)+'\n')
    return changed

def sync_app(repo_root: Path)->bool:
    p=repo_root/'integration/repository-lock.json'; lock=json.loads(p.read_text())
    direct={'zart':('ZairenkaiPrjctX/Zairenkai-ART','zart'),
            'zthermal':('ZairenkaiPrjctX/Zairenkai-ThermalTools','zthermal'),
            'afid-device-candidates':('ZairenkaiPrjctX/Zairenkai-Database-Source','afid-device-candidates'),
            'zie-run':('ZairenkaiPrjctX/Zairenkai-Intelligence-Engine','zie-run')}
    rows={x['id']:x for x in lock.get('components',[])}; changed=False
    for cid,(repo,component) in direct.items():
        row=rows.get(cid)
        if row is None or row.get('repository')!=repo: raise RuntimeError(f'App lock has incorrect/missing {cid}')
        pin=published_pin(repo,component,row['commit'])
        if pin is None:
            if row.get('release_artifact',{}).get('source_commit')!=row['commit'] and 'release_artifact' in row:
                del row['release_artifact']; changed=True
            print(f'{cid}: '+('no published verified artifact; source-build fallback remains' if 'release_artifact' not in row else 'retained pin for same immutable source'))
        else:
            if row.get('release_artifact')!=pin: row['release_artifact']=pin; changed=True
            print(f'{cid}: pinned {pin["release_tag"]} sha256={pin["asset_sha256"]}')
    if changed: p.write_text(json.dumps(lock,indent=2,ensure_ascii=False)+'\n')
    return changed

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['modules','app'],required=True); ap.add_argument('--repo-root',type=Path,required=True); ns=ap.parse_args()
    try: changed=sync_modules(ns.repo_root) if ns.mode=='modules' else sync_app(ns.repo_root)
    except (RuntimeError,KeyError,ValueError) as e: raise SystemExit(f'artifact pin sync failed closed: {e}')
    print('Lock updated.' if changed else 'No artifact pins changed.')
