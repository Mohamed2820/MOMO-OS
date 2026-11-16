from pathlib import Path
import tempfile
import unittest
from intelligence.cell import CellRegistry, MomoCell

class MomoCellTests(unittest.TestCase):
    def test_scans_python_and_json_without_mutating_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ok.py').write_text('value = 1\n', encoding='utf-8')
            (root / 'bad.py').write_text('def broken(:\n', encoding='utf-8')
            (root / 'bad.json').write_text('{"x": }', encoding='utf-8')
            (root / 'README.md').write_text('test', encoding='utf-8')
            (root / 'docs').mkdir()
            (root / 'docs/ARCHITECTURE.md').write_text('test', encoding='utf-8')
            (root / 'docs/SECURITY.md').write_text('test', encoding='utf-8')
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            report = MomoCell().scan(root)
            codes = {finding.code for finding in report.findings}
            self.assertIn('PYTHON_SYNTAX', codes)
            self.assertIn('INVALID_JSON', codes)
            self.assertFalse(report.to_dict()['mutation_performed'])
            self.assertTrue(all(proposal.requires_approval for proposal in report.proposals))
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_registry_rejects_duplicate_names(self):
        registry = CellRegistry()
        checker = lambda _root, _path, _payload: ()
        registry.register('one', checker)
        with self.assertRaises(ValueError):
            registry.register('one', checker)

    def test_scan_skips_generated_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            (root / '.git').mkdir()
            (root / '.git/ignored.py').write_text('def broken(:', encoding='utf-8')
            report = MomoCell().scan(root)
            self.assertFalse(any(f.path.startswith('.git') for f in report.findings))

if __name__ == '__main__':
    unittest.main()
