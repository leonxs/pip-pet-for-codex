"""Extract transparent PNG frames and a portable manifest from the spritesheet."""

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=ROOT / "assets" / "pet.json")
    parser.add_argument("--input", type=Path, help="Override the spritesheet image path.")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "frames")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    source = args.input or args.metadata.parent / metadata["image"]
    width = metadata["spritesheet"]["cell_width"]
    height = metadata["spritesheet"]["cell_height"]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"name": metadata["name"], "cell_size": [width, height],
                "states": {}, "look": []}

    with Image.open(source) as image:
        if image.mode != "RGBA":
            raise ValueError("Expected an RGBA spritesheet; run scripts/validate.py first.")

        def save_frame(row, column, relative_path):
            target = args.output / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            bounds = (column * width, row * height,
                      (column + 1) * width, (row + 1) * height)
            image.crop(bounds).save(target)
            return relative_path.as_posix()

        for state in metadata["states"]:
            manifest["states"][state["name"]] = [
                save_frame(state["row"], column,
                           Path(state["name"]) / f"{column:02d}.png")
                for column in range(state["frames"])
            ]
        for frame in metadata["look"]["frames"]:
            path = save_frame(frame["row"], frame["column"],
                              Path("look") / f"{frame['index']:02d}.png")
            manifest["look"].append({"index": frame["index"],
                                     "angle_degrees": frame["angle_degrees"],
                                     "path": path})

    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    count = sum(len(frames) for frames in manifest["states"].values()) + len(manifest["look"])
    print(json.dumps({"frames": count, "manifest": "manifest.json"}))


if __name__ == "__main__":
    main()
