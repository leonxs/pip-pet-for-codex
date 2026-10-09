"""Check the Pip v2 spritesheet and print a JSON validation report."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
STATES = [
    ("idle", 6), ("running-right", 8), ("running-left", 8),
    ("waving", 4), ("jumping", 5), ("failed", 8),
    ("waiting", 6), ("running", 6), ("review", 6),
]


def validate(metadata_path, image_path=None):
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    image_path = image_path or metadata_path.parent / metadata["image"]
    errors = []
    spec = metadata["spritesheet"]
    states = metadata["states"]
    look = metadata["look"]
    expected_spec = {
        "columns": 8, "rows": 11, "cell_width": 192, "cell_height": 208,
        "width": 1536, "height": 2288, "mode": "RGBA",
    }
    if metadata.get("version") != 2:
        errors.append("Metadata version must be 2.")
    if any(spec.get(key) != value for key, value in expected_spec.items()):
        errors.append("Metadata must describe the 8 x 11, 192 x 208 RGBA grid.")
    expected_states = [
        {"name": name, "row": row, "frames": count}
        for row, (name, count) in enumerate(STATES)
    ]
    if states != expected_states:
        errors.append("Metadata must contain all 9 states in their specified rows.")
    expected_look = [
        {"index": index, "row": 9 + index // 8, "column": index % 8,
         "angle_degrees": index * 22.5}
        for index in range(16)
    ]
    if (look.get("frames") != expected_look or look.get("angle_origin") != "up"
            or look.get("direction") != "clockwise"
            or look.get("angle_step_degrees") != 22.5):
        errors.append("Metadata must contain 16 clockwise look directions starting at up.")

    checksum = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if checksum != spec.get("sha256"):
        errors.append("Spritesheet SHA-256 does not match metadata.")
    with Image.open(image_path) as image:
        image.load()
        mode = image.mode
        size = image.size
        if mode != "RGBA":
            errors.append(f"Image mode is {mode}; expected RGBA.")
        if size != (1536, 2288):
            errors.append(f"Image size is {size}; expected (1536, 2288).")
        used_frames = empty_cells = 0
        transparent_rgb_pixels = None
        if mode == "RGBA":
            red, green, blue, alpha = image.split()
            invisible = alpha.point(lambda value: 255 if value == 0 else 0)
            rgb = ImageChops.lighter(ImageChops.lighter(red, green), blue)
            hidden_rgb = ImageChops.multiply(rgb, invisible)
            transparent_rgb_pixels = sum(hidden_rgb.histogram()[1:])
            if transparent_rgb_pixels:
                errors.append(f"{transparent_rgb_pixels} transparent pixels contain nonzero RGB.")
            if size == (1536, 2288):
                row_counts = [count for _, count in STATES] + [8, 8]
                for row, count in enumerate(row_counts):
                    for column in range(8):
                        bounds = (column * 192, row * 208,
                                  (column + 1) * 192, (row + 1) * 208)
                        bbox = alpha.crop(bounds).getbbox()
                        if column < count:
                            used_frames += 1
                            if bbox is None:
                                errors.append(f"Used cell ({row}, {column}) is empty.")
                            elif (bbox[0] == 0 or bbox[1] == 0
                                  or bbox[2] == 192 or bbox[3] == 208):
                                errors.append(f"Used cell ({row}, {column}) touches its border.")
                        else:
                            empty_cells += 1
                            if bbox is not None:
                                errors.append(f"Unused cell ({row}, {column}) is not transparent.")
        if used_frames != 73 or empty_cells != 15:
            errors.append("Expected 73 used frames and 15 transparent unused cells.")

    return {
        "ok": not errors,
        "image": image_path.name,
        "sha256": checksum,
        "mode": mode,
        "size": list(size),
        "state_count": len(states),
        "look_count": len(look.get("frames", [])),
        "used_frames": used_frames,
        "empty_cells": empty_cells,
        "transparent_pixels_with_rgb": transparent_rgb_pixels,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=ROOT / "assets" / "pet.json")
    parser.add_argument("--input", type=Path, help="Override the spritesheet image path.")
    parser.add_argument("--output", type=Path, help="Also save the JSON report to this path.")
    args = parser.parse_args()
    try:
        report = validate(args.metadata, args.input)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"ok": False, "errors": [str(error)]}
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
