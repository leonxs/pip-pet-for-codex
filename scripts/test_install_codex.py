"""Exercise install/update safety in retained, isolated directories under work/."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

import install_codex


class InstallerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workspace = install_codex.ROOT / "work"
        workspace.mkdir(exist_ok=True)
        cls.artifacts = Path(tempfile.mkdtemp(prefix="installer-update-check-", dir=workspace))
        cls.source = cls.artifacts / "source"
        for name in ("assets/pet.json", "assets/spritesheet.png", "codex/pet.json"):
            destination = cls.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(install_codex.ROOT / name, destination)
        print(f"Installer check artifacts: {cls.artifacts}")

    def setUp(self):
        self.home = self.artifacts / self._testMethodName
        self.source_patch = patch.object(install_codex, "ROOT", self.source)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    def package(self, home=None):
        return (home or self.home) / "pets" / "pip"

    def package_bytes(self, home=None):
        return {name: (self.package(home) / name).read_bytes()
                for name in ("pet.json", "spritesheet.png")}

    def old_package(self):
        install_codex.install(self.home)
        manifest_path = self.package() / "pet.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["description"] = "Previous Pip package for the update safety check."
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        marker = PngImagePlugin.PngInfo()
        marker.add_text("test-version", "previous-package")
        with Image.open(self.source / "assets/spritesheet.png") as image:
            image.save(self.package() / "spritesheet.png", pnginfo=marker)
        return self.package_bytes()

    def assert_current_package(self):
        self.assertEqual((self.package() / "pet.json").read_bytes(),
                         (self.source / "codex/pet.json").read_bytes())
        self.assertEqual((self.package() / "spritesheet.png").read_bytes(),
                         (self.source / "assets/spritesheet.png").read_bytes())

    def test_first_install_and_idempotence(self):
        self.assertEqual(install_codex.install(self.home)["action"], "installed")
        first = self.package_bytes()
        self.assertEqual(install_codex.install(self.home)["action"], "unchanged")
        self.assertEqual(install_codex.install(self.home, update=True)["action"], "unchanged")
        self.assertEqual(first, self.package_bytes())
        self.assertFalse((self.package() / ".backups").exists())
        self.assert_current_package()

    def test_default_refuses_conflict(self):
        original = self.old_package()
        with self.assertRaisesRegex(ValueError, "Existing file differs"):
            install_codex.install(self.home)
        self.assertEqual(original, self.package_bytes())
        self.assertFalse((self.package() / ".backups").exists())

    def test_update_backs_up_and_replaces(self):
        original = self.old_package()
        result = install_codex.install(self.home, update=True)
        self.assertEqual(result["action"], "updated")
        backup = Path(result["backup_directory"])
        self.assertTrue(backup.resolve().is_relative_to(self.package().resolve()))
        for name, data in original.items():
            self.assertEqual((backup / name).read_bytes(), data)
        self.assert_current_package()
        self.assertFalse(list(self.package().glob(".update-*")))
        self.assertEqual(install_codex.install(self.home, update=True)["action"], "unchanged")
        self.assertEqual(len(list((self.package() / ".backups").iterdir())), 1)

    def test_update_rejects_wrong_identity(self):
        for field, invalid in (("id", "other-pet"), ("displayName", "Other"),
                               ("spriteVersionNumber", 1),
                               ("spritesheetPath", "../other.png")):
            with self.subTest(field=field):
                check_home = self.home / field
                install_codex.install(check_home)
                path = self.package(check_home) / "pet.json"
                manifest = json.loads(path.read_text())
                manifest[field] = invalid
                path.write_text(json.dumps(manifest), encoding="utf-8")
                original = self.package_bytes(check_home)
                with self.assertRaisesRegex(ValueError, "existing manifest"):
                    install_codex.install(check_home, update=True)
                self.assertEqual(original, self.package_bytes(check_home))
                self.assertFalse((self.package(check_home) / ".backups").exists())

    def test_update_rejects_linked_directory(self):
        target = self.home / "unrelated-pet"
        target.mkdir(parents=True)
        (target / "sentinel.txt").write_text("Preserve this directory.")
        self.package().parent.mkdir()
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(target), str(self.package()))
        else:
            self.package().symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "linked directory"):
            install_codex.install(self.home, update=True)
        self.assertEqual([path.name for path in target.iterdir()], ["sentinel.txt"])

    def test_update_rejects_incomplete_package(self):
        for present in ("pet.json", "spritesheet.png"):
            with self.subTest(present=present):
                check_home = self.home / present
                destination = self.package(check_home)
                destination.mkdir(parents=True)
                source = self.source / ("codex" if present == "pet.json" else "assets") / present
                original = source.read_bytes()
                (destination / present).write_bytes(original)
                with self.assertRaisesRegex(ValueError, "incomplete Pip package"):
                    install_codex.install(check_home, update=True)
                self.assertEqual([path.name for path in destination.iterdir()], [present])
                self.assertEqual((destination / present).read_bytes(), original)

    def test_update_rejects_linked_backup_directory(self):
        original = self.old_package()
        target = self.home / "unrelated-backups"
        target.mkdir()
        (target / "sentinel.txt").write_text("Preserve this directory.")
        backup_root = self.package() / ".backups"
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(target), str(backup_root))
        else:
            backup_root.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsafe backup directory"):
            install_codex.install(self.home, update=True)
        self.assertEqual(original, self.package_bytes())
        self.assertEqual([path.name for path in target.iterdir()], ["sentinel.txt"])

    def test_backup_failure_does_not_replace_original(self):
        original = self.old_package()
        real_write = install_codex.write_new_file

        def fail_sprite_backup(path, data):
            if ".backups" in path.parts and path.name == "spritesheet.png":
                raise OSError("Simulated backup disk full")
            return real_write(path, data)

        with patch.object(install_codex, "write_new_file", side_effect=fail_sprite_backup):
            with self.assertRaisesRegex(OSError, "backup disk full"):
                install_codex.install(self.home, update=True)
        self.assertEqual(original, self.package_bytes())
        self.assertFalse(list(self.package().glob(".update-*")))

    def test_rollback_preserves_concurrent_edit(self):
        original = self.old_package()
        concurrent_manifest = b'{"description": "Concurrent local edit"}'
        real_replace = os.replace
        replacement_count = 0

        def change_manifest_after_sprite_replace(source, target):
            nonlocal replacement_count
            replacement_count += 1
            result = real_replace(source, target)
            if replacement_count == 1:
                (self.package() / "pet.json").write_bytes(concurrent_manifest)
            return result

        with patch.object(install_codex.os, "replace", side_effect=change_manifest_after_sprite_replace):
            with self.assertRaisesRegex(OSError, "automatic recovery failed"):
                install_codex.install(self.home, update=True)
        self.assertEqual((self.package() / "pet.json").read_bytes(), concurrent_manifest)
        self.assertEqual((self.package() / "spritesheet.png").read_bytes(),
                         original["spritesheet.png"])
        backups = list((self.package() / ".backups").iterdir())
        self.assertEqual(len(backups), 1)
        for name, data in original.items():
            self.assertEqual((backups[0] / name).read_bytes(), data)

    def test_update_rolls_back_on_replace_failure(self):
        original = self.old_package()
        real_replace = os.replace
        replacement_count = 0

        def fail_second_replace(source, target):
            nonlocal replacement_count
            replacement_count += 1
            if replacement_count == 2:
                raise PermissionError("Simulated manifest write lock")
            return real_replace(source, target)

        with patch.object(install_codex.os, "replace", side_effect=fail_second_replace):
            with self.assertRaisesRegex(OSError, "original package restored"):
                install_codex.install(self.home, update=True)
        self.assertEqual(original, self.package_bytes())
        backups = list((self.package() / ".backups").iterdir())
        self.assertEqual(len(backups), 1)
        for name, data in original.items():
            self.assertEqual((backups[0] / name).read_bytes(), data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
