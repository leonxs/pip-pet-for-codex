"""Pin README artwork and install URLs to a verified Git commit of the assets."""

import argparse
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qsl, quote, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/leonxs/pip-pet-for-codex"
RAW = "https://raw.githubusercontent.com/leonxs/pip-pet-for-codex"
ASSET_PATH = r"(?:assets|previews)/[\w.-]+\.(?:png|gif|json)"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def pin_readme(revision):
    commit = git("rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}").decode().strip()
    readme = ROOT / "README.md"
    original = readme.read_text(encoding="utf-8")
    paths = {"assets/spritesheet.png"}

    def replace_artwork(match):
        url = match[1]
        if re.fullmatch(ASSET_PATH, url):
            path = url
        else:
            remote = re.fullmatch(
                rf"(?:{re.escape(RAW)}/|{re.escape(REPOSITORY)}/blob/)[^/]+/({ASSET_PATH})",
                url,
            )
            if remote is None:
                return match[0]
            path = remote[1]
        paths.add(path)
        return f"]({RAW}/{commit}/{path})"

    updated = re.sub(r"\]\(([^)]+)\)", replace_artwork, original)

    def replace_install(match):
        parameters = dict(parse_qsl(urlsplit(match[0]).query))
        parameters["imageUrl"] = f"{RAW}/{commit}/assets/spritesheet.png"
        return "codex://pets/install?" + urlencode(parameters, quote_via=quote)

    updated = re.sub(r"codex://pets/install\?[^\s)'\"]+", replace_install, updated)
    # Refuse stale pins: every linked file must already exist in the chosen
    # commit and match the checkout, before the README is changed at all.
    for path in sorted(paths):
        committed = git("show", f"{commit}:{path}")
        current = (ROOT / path).read_bytes()
        if path.endswith(".json"):
            committed = committed.replace(b"\r\n", b"\n")
            current = current.replace(b"\r\n", b"\n")
        if committed != current:
            raise ValueError(f"{path} differs from {commit[:7]}; commit rebuilt assets first.")
    if updated != original:
        readme.write_text(updated, encoding="utf-8", newline="\n")
    return commit, len(paths), updated != original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", help="Commit containing the current atlas and previews.")
    args = parser.parse_args()
    try:
        commit, count, changed = pin_readme(args.revision)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Cannot pin README assets: {error}\n")
    print(f"Verified {count} artwork files at {commit}; README {'updated' if changed else 'unchanged'}.")


if __name__ == "__main__":
    main()
