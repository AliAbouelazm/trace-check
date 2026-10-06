import importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_bundle',ROOT/'scripts/package_public_review.py');bundle=importlib.util.module_from_spec(spec);spec.loader.exec_module(bundle)
class PublicBundleTests(unittest.TestCase):
    def test_private_review_excludes_model_and_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'review.zip';result=bundle.package(output)
            self.assertFalse(result['publication_approved'])
            with zipfile.ZipFile(output) as archive:
                names=set(archive.namelist())
                self.assertEqual(names,set(bundle.ASSETS)|{'_headers','PUBLICATION-BLOCKED.txt','asset-manifest.json'})
                self.assertNotIn('review-model-data.js',names)
                self.assertIn(b'INCOMPLETE PRIVATE REVIEW BUNDLE',archive.read('index.html'))
                self.assertIn(b"$('ml-enable').disabled = true;",archive.read('app.js'))
                self.assertIn(b"ML disabled in this incomplete review bundle.'; return;",archive.read('app.js'))
                self.assertFalse(json.loads(archive.read('asset-manifest.json'))['model_included'])
                self.assertIn(b"frame-ancestors 'none'",archive.read('_headers'))
                self.assertIn(b'privacy/license clearance pending',archive.read('PUBLICATION-BLOCKED.txt'))
    def test_complete_candidate_preserves_model_and_retains_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'complete.zip';result=bundle.package(output,complete=True)
            self.assertTrue(result['model_included']);self.assertFalse(result['publication_approved'])
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()),set(bundle.ASSETS)|{'review-model-data.js','_headers','RELEASE-REVIEW.txt','asset-manifest.json'})
                self.assertEqual(archive.read('review-model-data.js'),(ROOT/'web/review-model-data.js').read_bytes())
                self.assertEqual(archive.read('app.js'),(ROOT/'web/app.js').read_bytes())
                self.assertNotIn(b'INCOMPLETE PRIVATE REVIEW BUNDLE',archive.read('index.html'))
                notice=archive.read('THIRD-PARTY-NOTICES.txt')
                self.assertIn(b'Apache License',notice);self.assertIn(b'Copyright (c) 2025 Sierra Research',notice)
                self.assertIn(b'No raw GAIA dataset',notice)
