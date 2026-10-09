"""Install the validated Pip v2 pet into the local Codex pets directory."""

import argparse
import json
import os
from pathlib import Path

from validate import validate


ROOT = Path(__file__).resolve().parents[1]


def is_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def install(codex_home):
    report = validate(ROOT / "assets" / "pet.json")
    if not report["ok"]:
        raise ValueError("Spritesheet validation failed: " + "; ".join(report["errors"]))

    manifest_path = ROOT / "codex" / "pet.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("id") != "pip" or manifest.get("displayName") != "Pip"
            or manifest.get("spriteVersionNumber") != 2
            or manifest.get("spritesheetPath") != "spritesheet.png"
            or not isinstance(manifest.get("description"), str)):
        raise ValueError("The Codex manifest must describe Pip and its v2 PNG spritesheet.")

    codex_home = codex_home.expanduser().resolve()
    destination = codex_home / "pets" / "pip"
    files = {
        "pet.json": manifest_path.read_bytes(),
        "spritesheet.png": (ROOT / "assets" / "spritesheet.png").read_bytes(),
    }
    # Check the complete destination before writing either file. Never replace
    # a different pet or a locally modified installation without user action.
    if is_link(destination.parent) or is_link(destination):
        raise ValueError(f"Refusing to install through a linked directory: {destination}")
    if not destination.resolve().is_relative_to(codex_home):
        raise ValueError(f"Installation path is outside Codex home: {destination}")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Installation path is not a directory: {destination}")
    for name, data in files.items():
        target = destination / name
        if is_link(target):
            raise ValueError(f"Refusing to replace a linked file: {target}")
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise ValueError(f"Existing file differs; review it before installing: {target}")

    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = destination / name
        try:
            with target.open("xb") as output:
                output.write(data)
        except FileExistsError:
            if is_link(target) or not target.is_file() or target.read_bytes() != data:
                raise ValueError(f"Existing file differs; review it before installing: {target}")
        if target.read_bytes() != data:
            raise OSError(f"Installed file verification failed: {target}")

    return {
        "ok": True,
        "pet_id": "pip",
        "sprite_version": 2,
        "installation_directory": str(destination),
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
    args = parser.parse_args()
    try:
        result = install(args.codex_home)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "errors": [str(error)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
