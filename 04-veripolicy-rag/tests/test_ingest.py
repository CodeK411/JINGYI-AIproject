from __future__ import annotations

import unittest
from pathlib import Path

from veripolicy.ingest import load_corpus, parse_document


ROOT = Path(__file__).resolve().parents[1]


class IngestTests(unittest.TestCase):
    def test_corpus_is_parsed_into_stable_chunks(self) -> None:
        chunks = load_corpus(ROOT / "data" / "corpus")
        self.assertGreaterEqual(len(chunks), 80)
        self.assertEqual(len({chunk.chunk_id for chunk in chunks}), len(chunks))
        self.assertTrue(any(chunk.rules for chunk in chunks))
        self.assertTrue(all("<!-- rule:" not in chunk.text for chunk in chunks))

    def test_frontmatter_metadata(self) -> None:
        document = parse_document(ROOT / "data" / "corpus" / "travel_cn_2025.md")
        self.assertEqual(document.doc_id, "travel_cn_2025")
        self.assertEqual(document.regions, ("CN",))
        self.assertEqual(document.effective_from.isoformat(), "2025-01-01")


if __name__ == "__main__":
    unittest.main()

