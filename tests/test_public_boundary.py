from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = [
    'evidence/results', 'evidence/freezes', 'archive/historical', 'manuscript',
    'protected', 'reserve', 'private_data'
]

# Construct sensitive signatures at runtime so the signatures themselves are not
# stored verbatim in this public demonstration repository.
FORBIDDEN_TERMS = [
    ''.join(['0.385726', '190476']),
    ''.join(['0.386569', '497922']),
    ''.join(['0.330033', '352154']),
    ''.join(['0.441170', '240546']),
    ''.join(['840 ', 'protected']),
    ''.join(['HOLDOUT_', '2024_ORIGIN']),
    ''.join(['RESERVE_', '2025_ORIGIN']),
]

class TestPublicBoundary(unittest.TestCase):
    def test_forbidden_paths_absent(self):
        for rel in FORBIDDEN_PATHS:
            self.assertFalse((ROOT / rel).exists(), rel)

    def test_private_result_signatures_absent(self):
        for p in ROOT.rglob('*'):
            if (p.is_file() and '.git' not in p.parts
                    and p.suffix.lower() in {'.md','.py','.sql','.yml','.yaml','.txt','.csv','.json'}):
                text = p.read_text(encoding='utf-8', errors='ignore')
                if p.name == 'test_public_boundary.py':
                    continue
                for term in FORBIDDEN_TERMS:
                    self.assertNotIn(term, text, f'{term} in {p}')

if __name__ == '__main__':
    unittest.main()
