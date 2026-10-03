"""Setup guards without downloading tools or compiling dependencies."""
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools.setup import download, extract, setup_host


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_cached_download_and_checksum_failure(self):
        output = self.root / "download.tar.gz"
        output.write_bytes(b"verified")
        expected = hashlib.sha256(b"verified").hexdigest()
        with patch("tools.setup.execute") as execute:
            download("https://example.invalid/archive", output, expected)
            execute.assert_not_called()
            def corrupt(args):
                Path(args[args.index("--output") + 1]).write_bytes(b"corrupt")
            execute.side_effect = corrupt
            with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                download("https://example.invalid/archive", output, "0" * 64)
        self.assertEqual(output.read_bytes(), b"verified")
        self.assertFalse(output.with_suffix(".partial").exists())

    def test_archive_paths_and_links_cannot_escape(self):
        for is_link in (False, True):
            with self.subTest(link=is_link):
                archive = self.root / "archive.tar.gz"
                with tarfile.open(archive, "w:gz") as stream:
                    item = tarfile.TarInfo("bin/link" if is_link else "../escaped")
                    if is_link:
                        item.type = tarfile.SYMTYPE
                        item.linkname = "../../escaped"
                        stream.addfile(item)
                    else:
                        item.size = 1
                        stream.addfile(item, io.BytesIO(b"x"))
                with self.assertRaisesRegex(RuntimeError, "escapes"):
                    extract(archive, self.root / "install")
                self.assertFalse((self.root / "escaped").exists())

    def test_pinned_checkout_preserves_changes(self):
        host = self.root / ".deps/gpui-dotnet"
        host.mkdir(parents=True)
        pin = {"url": "https://github.com/example/host.git", "revision": "1" * 40}
        with patch("tools.setup.ROOT", self.root), patch("tools.setup.execute") as execute:
            execute.return_value = "2" * 40 + "\n"
            with self.assertRaisesRegex(RuntimeError, "different revision"):
                setup_host(pin)
            execute.assert_called_once()
            execute.reset_mock()
            execute.side_effect = [pin["revision"] + "\n", " M source.rs\n"]
            with self.assertRaisesRegex(RuntimeError, "local changes"):
                setup_host(pin)
            self.assertEqual(execute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
