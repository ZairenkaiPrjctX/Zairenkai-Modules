# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/sync_component_artifacts.py'
spec=importlib.util.spec_from_file_location('artifact_pin_sync',SCRIPT)
sync=importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
class ArtifactPinSyncTests(unittest.TestCase):
 def test_published_exact_commit_pin_is_saved(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'components.lock.json'; rows=[{'name':n,'repository':f'ZairenkaiPrjctX/{repo}','commit':'a'*40} for n,repo in [('zairenkai-core','Zairenkai-Core'),('zairenkai-fas','Zairenkai-FAS'),('zairenkai-tuning','Zairenkai-Tuning')]]
   p.write_text(json.dumps({'components':rows}))
   def fake(repo,component,commit): return {'repository':repo,'component':component,'source_commit':commit,'release_tag':'artifact-'+commit,'asset_name':'bundle.tar.gz','asset_sha256':'b'*64,'asset_size_bytes':123,'manifest_name':'artifact-manifest.json','manifest_sha256':'c'*64}
   with patch.object(sync,'published_pin',side_effect=fake):
    self.assertTrue(sync.sync_modules(Path(td)))
   data=json.loads(p.read_text())
   self.assertTrue(all(x['release_artifact']['source_commit']==x['commit'] for x in data['components']))
 def test_stale_pin_is_removed_if_source_commit_changes_without_release(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'components.lock.json'; p.write_text(json.dumps({'components':[{'name':'zairenkai-core','repository':'ZairenkaiPrjctX/Zairenkai-Core','commit':'b'*40,'release_artifact':{'source_commit':'a'*40,'release_tag':'artifact-'+'a'*40}}]}))
   with patch.object(sync,'published_pin',return_value=None): self.assertTrue(sync.sync_modules(Path(td)))
   self.assertNotIn('release_artifact',json.loads(p.read_text())['components'][0])
 def test_old_pin_for_same_source_is_retained_if_release_lookup_has_no_result(self):
  with tempfile.TemporaryDirectory() as td:
   pin={'source_commit':'a'*40,'release_tag':'artifact-'+'a'*40,'asset_sha256':'b'*64}
   p=Path(td)/'components.lock.json'; p.write_text(json.dumps({'components':[{'name':'zairenkai-core','repository':'ZairenkaiPrjctX/Zairenkai-Core','commit':'a'*40,'release_artifact':pin}]}))
   with patch.object(sync,'published_pin',return_value=None): self.assertFalse(sync.sync_modules(Path(td)))
   self.assertEqual(pin,json.loads(p.read_text())['components'][0]['release_artifact'])
if __name__=='__main__': unittest.main()
