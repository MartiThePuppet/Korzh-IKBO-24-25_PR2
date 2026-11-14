import tempfile
import unittest
from pathlib import Path

from aptgraph.config import Config, ConfigError
from aptgraph.graph import build_graph, reverse_dependencies
from aptgraph.repository import AptRepository


ROOT = Path(__file__).parents[1]


class AppTests(unittest.TestCase):
    def test_config_and_repository(self):
        config = Config.from_csv(ROOT / "examples/demo.csv")
        packages = AptRepository(config.resolved_repository(ROOT / "examples/demo.csv"), True).load()
        self.assertEqual(packages["A"], ["B", "C"])

    def test_recursive_dfs_and_cycle(self):
        packages = AptRepository(ROOT / "examples/repository.json", True).load()
        graph = build_graph(packages, "F")
        self.assertEqual(set(graph.edges), {"F", "G", "H"})
        self.assertIn(("H", "F"), graph.cycles)

    def test_filter(self):
        packages = AptRepository(ROOT / "examples/repository.json", True).load()
        graph = build_graph(packages, "A", "D")
        self.assertNotIn("D", graph.edges)
        self.assertEqual(graph.edges["A"], ["B", "C"])

    def test_reverse(self):
        packages = AptRepository(ROOT / "examples/repository.json", True).load()
        graph = reverse_dependencies(packages, "D")
        self.assertEqual(set(graph.edges), {"D", "B", "C", "A", "X", "Y"})

    def test_invalid_config(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.csv"
            path.write_text("key,value\npackage,A\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                Config.from_csv(path)


if __name__ == "__main__":
    unittest.main()
