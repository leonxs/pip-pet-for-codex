"""Create white-background GIF previews and a full-size contact sheet."""

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=ROOT / "assets" / "pet.json")
    parser.add_argument("--input", type=Path, help="Override the spritesheet image path.")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "previews")
    parser.add_argument("--duration", type=int, default=120,
                        help="Preview frame duration in milliseconds (default: 120).")
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error("--duration must be positive")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    source = args.input or args.metadata.parent / metadata["image"]
    width = metadata["spritesheet"]["cell_width"]
    height = metadata["spritesheet"]["cell_height"]
    args.output.mkdir(parents=True, exist_ok=True)
    gif_count = 0

    with Image.open(source) as image:
        if image.mode != "RGBA":
            raise ValueError("Expected an RGBA spritesheet; run scripts/validate.py first.")

        def preview_frame(row, column):
            frame = image.crop((column * width, row * height,
                                (column + 1) * width, (row + 1) * height))
            background = Image.new("RGBA", frame.size, "white")
            return Image.alpha_composite(background, frame).convert("RGB")

        def save_gif(frames, name):
            frames[0].save(args.output / name, save_all=True,
                           append_images=frames[1:], duration=args.duration,
                           loop=0, disposal=2, optimize=False)

        for state in metadata["states"]:
            frames = [preview_frame(state["row"], column)
                      for column in range(state["frames"])]
            save_gif(frames, state["name"] + ".gif")
            gif_count += 1
        look_frames = [preview_frame(frame["row"], frame["column"])
                       for frame in metadata["look"]["frames"]]
        save_gif(look_frames, "look-loop.gif")
        gif_count += 1
        background = Image.new("RGBA", image.size, "white")
        Image.alpha_composite(background, image).convert("RGB").save(
            args.output / "contact-sheet.png")

    print(json.dumps({"gifs": gif_count, "contact_sheet": "contact-sheet.png",
                      "duration_ms": args.duration}))


if __name__ == "__main__":
    main()
