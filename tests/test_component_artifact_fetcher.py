# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/fetch_component_artifact.py'
spec = importlib.util.spec_from_file_location('artifact_fetcher', SCRIPT)
fetcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(fetcher)

class ComponentArtifactFetcherTests(unittest.TestCase):
    def archive(self, files):
        b=io.BytesIO()
        with tarfile.open(fileobj=b, mode='w:gz') as tf:
            for name,data in files.items():
                info=tarfile.TarInfo(name); info.size=len(data); info.mode=0o644
                tf.addfile(info, io.BytesIO(data))
        return b.getvalue()

    def manifest(self, archive, files):
        return {'schema_version':1, 'repository':'ZairenkaiPrjctX/Zairenkai-Core',
                'component':'zairenkai-core', 'source_commit':'a'*40, 'archive_format':'tar.gz',
                'assets':[{'name':'core.tar.gz','size_bytes':len(archive),'sha256':hashlib.sha256(archive).hexdigest()}],
                'files':[{'path':n,'size_bytes':len(v),'sha256':hashlib.sha256(v).hexdigest(),'executable':False} for n,v in files.items()]}

    def test_manifest_accepts_matching_repo_component_commit_and_archive(self):
        files={'component.json':b'{"schema":1}\n','bin/zcored':b'core'}
        archive=self.archive(files); m=self.manifest(archive,files)
        fetcher.validate_manifest(m, repository='ZairenkaiPrjctX/Zairenkai-Core', component='zairenkai-core', commit='a'*40, asset_name='core.tar.gz', archive=archive)

    def test_manifest_rejects_commit_mismatch_and_archive_tampering(self):
        files={'component.json':b'{}'}; archive=self.archive(files); m=self.manifest(archive,files)
        with self.assertRaises(fetcher.ArtifactError):
            fetcher.validate_manifest(m, repository='ZairenkaiPrjctX/Zairenkai-Core', component='zairenkai-core', commit='b'*40, asset_name='core.tar.gz', archive=archive)
        with self.assertRaises(fetcher.ArtifactError):
            fetcher.validate_manifest(m, repository='ZairenkaiPrjctX/Zairenkai-Core', component='zairenkai-core', commit='a'*40, asset_name='core.tar.gz', archive=archive+b'x')

    def test_extract_verifies_each_file_hash_and_restores_executable_mode(self):
        files={'bin/zcored':b'core'}; archive=self.archive(files); m=self.manifest(archive,files); m['files'][0]['executable']=True
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/'out'; n=fetcher.verify_and_extract(archive,m,dest)
            self.assertEqual(1,n); self.assertEqual(b'core',(dest/'bin/zcored').read_bytes())
            self.assertTrue((dest/'bin/zcored').stat().st_mode & 0o111)

    def test_extract_rejects_manifest_hash_mismatch(self):
        files={'bin/zcored':b'core'}; archive=self.archive(files); m=self.manifest(archive,files); m['files'][0]['sha256']='0'*64
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(fetcher.ArtifactError): fetcher.verify_and_extract(archive,m,Path(td)/'out')

    def test_extract_rejects_path_traversal(self):
        files={'../outside':b'bad'}; archive=self.archive(files); m=self.manifest(archive,files)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(fetcher.ArtifactError): fetcher.verify_and_extract(archive,m,Path(td)/'out')
            self.assertFalse((Path(td)/'outside').exists())

    def test_unpinned_component_uses_distinct_fallback_exit(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'lock.json'; p.write_text(json.dumps({'components':[{'name':'zairenkai-core','repository':'ZairenkaiPrjctX/Zairenkai-Core','commit':'a'*40}]}))
            with self.assertRaises(fetcher.UnpinnedArtifact): fetcher.fetch(p,'zairenkai-core',Path(td)/'out',collection='components')

if __name__=='__main__': unittest.main()
