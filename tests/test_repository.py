import gzip
import lzma
import unittest

from aptgraph.repository import AptRepository, RepositoryError


INDEX = b"""Package: demo
Depends: missing | lib:any (>= 1),
 virtual
Pre-Depends: base

Package: lib

Package: base

Package: provider
Provides: virtual

"""


class RepositoryTests(unittest.TestCase):
    def test_alternatives_versions_predepends_provides(self):
        packages = AptRepository._parse_packages(INDEX)
        self.assertEqual(packages["demo"], ["base", "lib", "provider"])

    def test_gzip(self):
        self.assertEqual(AptRepository._parse_packages(gzip.compress(INDEX)),
                         AptRepository._parse_packages(INDEX))

    def test_xz(self):
        self.assertEqual(AptRepository._parse_packages(lzma.compress(INDEX)),
                         AptRepository._parse_packages(INDEX))

    def test_empty_index(self):
        with self.assertRaises(RepositoryError):
            AptRepository._parse_packages(b"not an index")

    def test_missing_leaf(self):
        packages = AptRepository._parse_packages(
            b"Package: demo\nDepends: unknown (>= 2)\n")
        self.assertEqual(packages["demo"], ["unknown"])


if __name__ == "__main__":
    unittest.main()
