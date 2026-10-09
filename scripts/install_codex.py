"""Install the validated Pip v2 pet into the local Codex pets directory."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from validate import validate


ROOT = Path(__file__).resolve().parents[1]


def is_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def check_manifest(data, label):
    manifest = json.loads(data.decode("utf-8"))
    if (not isinstance(manifest, dict)
            or manifest.get("id") != "pip" or manifest.get("displayName") != "Pip"
            or manifest.get("spriteVersionNumber") != 2
            or manifest.get("spritesheetPath") != "spritesheet.png"
            or not isinstance(manifest.get("description"), str)):
        raise ValueError(f"{label} must describe Pip and its v2 PNG spritesheet.")


def check_directory(codex_home, destination):
    if is_link(destination.parent) or is_link(destination):
        raise ValueError(f"Refusing to install through a linked directory: {destination}")
    if not destination.resolve().is_relative_to(codex_home):
        raise ValueError(f"Installation path is outside Codex home: {destination}")
    for directory in (destination.parent, destination):
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Installation path is not a directory: {directory}")


def write_new_file(path, data):
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    if path.read_bytes() != data:
        raise OSError(f"Written file verification failed: {path}")


def update_package(codex_home, destination, files, original):
    backup_root = destination / ".backups"
    if (is_link(backup_root)
            or (backup_root.exists() and not backup_root.is_dir())
            or not backup_root.resolve().is_relative_to(destination)):
        raise ValueError(f"Unsafe backup directory: {backup_root}")
    check_directory(codex_home, destination)
    for name, data in original.items():
        target = destination / name
        if is_link(target) or not target.is_file() or target.read_bytes() != data:
            raise ValueError(f"Existing package changed during preflight: {target}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    identifier = f"{stamp}-{uuid.uuid4().hex[:8]}"
    backup = backup_root / identifier
    staging = destination / f".update-{identifier}"
    backup.mkdir(parents=True, exist_ok=False)
    for name, data in original.items():
        write_new_file(backup / name, data)

    replaced = []
    try:
        staging.mkdir(exist_ok=False)
        for name, data in files.items():
            write_new_file(staging / name, data)
        check_directory(codex_home, destination)
        # Keep the manifest last. Each replacement is atomic on the same volume.
        for name in ("spritesheet.png", "pet.json"):
            target = destination / name
            if (is_link(target) or not target.is_file()
                    or target.read_bytes() != original[name]):
                raise ValueError(f"Existing package changed during update: {target}")
            os.replace(staging / name, target)
            replaced.append(name)
        for name, data in files.items():
            target = destination / name
            if is_link(target) or target.read_bytes() != data:
                raise OSError(f"Installed file verification failed: {target}")
    except (OSError, ValueError) as error:
        try:
            check_directory(codex_home, destination)
            for name in reversed(replaced):
                target = destination / name
                # Do not overwrite a concurrent, unrelated edit during recovery.
                if is_link(target) or target.read_bytes() != files[name]:
                    raise OSError(f"Cannot safely restore changed file: {target}")
                recovery = staging / f"restore-{name}"
                write_new_file(recovery, original[name])
                os.replace(recovery, target)
            for name, data in original.items():
                if (destination / name).read_bytes() != data:
                    raise OSError(f"Restored file verification failed: {name}")
        except (OSError, ValueError) as recovery_error:
            raise OSError(f"Update failed: {error}; automatic recovery failed: "
                          f"{recovery_error}. Original package backup: {backup}") from error
        raise OSError(f"Update failed; original package restored: {error}. "
                      f"Backup: {backup}") from error
    # Only remove our now-empty staging directory; retain every backup.
    staging.rmdir()
    return backup


def install(codex_home, update=False):
    report = validate(ROOT / "assets" / "pet.json")
    if not report["ok"]:
        raise ValueError("Spritesheet validation failed: " + "; ".join(report["errors"]))

    manifest_path = ROOT / "codex" / "pet.json"
    codex_home = codex_home.expanduser().resolve()
    destination = codex_home / "pets" / "pip"
    files = {
        "pet.json": manifest_path.read_bytes(),
        "spritesheet.png": (ROOT / "assets" / "spritesheet.png").read_bytes(),
    }
    check_manifest(files["pet.json"], "The Codex manifest")
    if hashlib.sha256(files["spritesheet.png"]).hexdigest() != report["sha256"]:
        raise ValueError("Source spritesheet changed during validation; run again.")
    # Check the complete destination before writing either file. Never replace
    # a different pet or a locally modified installation without user action.
    check_directory(codex_home, destination)
    original = {}
    for name, data in files.items():
        target = destination / name
        if is_link(target):
            raise ValueError(f"Refusing to replace a linked file: {target}")
        if target.exists():
            if not target.is_file():
                raise ValueError(f"Installation target is not a regular file: {target}")
            original[name] = target.read_bytes()
            if original[name] != data and not update:
                raise ValueError(f"Existing file differs; review it and use --update "
                                 f"to back up and replace Pip: {target}")

    backup = None
    action = "unchanged" if original == files else "installed"
    if update and original and original != files:
        if original.keys() != files.keys():
            raise ValueError("Cannot update an incomplete Pip package; both pet.json "
                             "and spritesheet.png must exist for backup.")
        check_manifest(original["pet.json"], "The existing manifest")
        backup = update_package(codex_home, destination, files, original)
        action = "updated"
    elif original != files:
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            target = destination / name
            check_directory(codex_home, destination)
            try:
                write_new_file(target, data)
            except FileExistsError:
                if is_link(target) or not target.is_file() or target.read_bytes() != data:
                    raise ValueError(f"Existing file differs; review it before installing: {target}")
            if target.read_bytes() != data:
                raise OSError(f"Installed file verification failed: {target}")

    return {
        "ok": True,
        "pet_id": "pip",
        "sprite_version": 2,
        "action": action,
        "installation_directory": str(destination),
        "backup_directory": str(backup) if backup else None,
        "spritesheet_sha256": report["sha256"],
        "next_step": "Open Settings > Pets, click Refresh, choose Pip, then use /pet to show it.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home", type=Path,
        default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"),
        help="Codex home directory (default: CODEX_HOME, otherwise ~/.codex).",
    )
    parser.add_argument("--update", action="store_true",
                        help="Back up and replace an existing verified Pip package.")
    args = parser.parse_args()
    try:
        result = install(args.codex_home, update=args.update)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "errors": [str(error)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
