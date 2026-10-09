"""Create frame-accurate GIFs, stills, and contact sheets from the final atlas."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = "#f5f1e9"
LABEL_COLOR = "#393f45"
STATE_LABELS = {
    "idle": "Idle", "running-right": "Run right", "running-left": "Run left",
    "waving": "Wave", "jumping": "Jump", "failed": "Disappointed",
    "waiting": "Waiting", "running": "Working", "review": "Review",
}
REPRESENTATIVE_FRAMES = {
    "idle": 0, "running-right": 2, "running-left": 2, "waving": 1,
    "jumping": 2, "failed": 3, "waiting": 2, "running": 2, "review": 2,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=ROOT / "assets" / "pet.json")
    parser.add_argument("--input", type=Path, help="Override the spritesheet image path.")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "previews")
    parser.add_argument("--duration", type=int, default=120,
                        help="Base frame duration in ms; idle endpoints hold longer (default: 120).")
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error("--duration must be positive")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    source = args.input or args.metadata.parent / metadata["image"]
    width = metadata["spritesheet"]["cell_width"]
    height = metadata["spritesheet"]["cell_height"]
    args.output.mkdir(parents=True, exist_ok=True)
    gif_count = 0
    generated_files = []

    with Image.open(source) as image:
        if image.mode != "RGBA":
            raise ValueError("Expected an RGBA spritesheet; run scripts/validate.py first.")

        def sprite_frame(row, column):
            return image.crop((column * width, row * height,
                               (column + 1) * width, (row + 1) * height))

        def preview_frame(row, column):
            frame = sprite_frame(row, column)
            background = Image.new("RGBA", frame.size, BACKGROUND)
            return Image.alpha_composite(background, frame).convert("RGB")

        def labeled_frame(frame, label):
            # Paste the entire cell unchanged so whitespace and motion stay intact.
            result = Image.new("RGB", (width + 64, height + 48), BACKGROUND)
            result.paste(frame, (32, 32))
            ImageDraw.Draw(result).text((12, 10), label, fill=LABEL_COLOR)
            return result

        def save_gif(frames, name, durations=None):
            nonlocal gif_count
            frames[0].save(args.output / name, save_all=True,
                           append_images=frames[1:],
                           duration=durations if durations is not None else args.duration,
                           loop=0, disposal=2, optimize=False)
            generated_files.append(name)
            gif_count += 1

        def save_png(frame, name):
            frame.save(args.output / name)
            generated_files.append(name)

        def state_durations(state):
            durations = [args.duration] * state["frames"]
            if state["name"] == "idle":
                durations[0] = args.duration * 3
                durations[-1] = args.duration * 2
            return durations

        states = {state["name"]: state for state in metadata["states"]}
        state_frames = {}
        all_frames = []
        all_durations = []
        for state in metadata["states"]:
            frames = [preview_frame(state["row"], column)
                      for column in range(state["frames"])]
            state_frames[state["name"]] = frames
            durations = state_durations(state)
            save_gif(frames, state["name"] + ".gif", durations)
            label = STATE_LABELS.get(state["name"], state["name"])
            all_frames.extend(labeled_frame(frame, label) for frame in frames)
            # Give each state a short settling pause in the overview animation.
            durations[-1] = max(durations[-1], args.duration * 2)
            all_durations.extend(durations)
        save_gif(all_frames, "all-states.gif", all_durations)

        transition_frames = (state_frames["idle"] + state_frames["jumping"]
                             + state_frames["idle"])
        transition_durations = (state_durations(states["idle"])
                                + state_durations(states["jumping"])
                                + state_durations(states["idle"]))
        save_gif(transition_frames, "idle-jump-idle.gif", transition_durations)

        look_frames = [preview_frame(frame["row"], frame["column"])
                       for frame in metadata["look"]["frames"]]
        save_gif(look_frames, "look-loop.gif")
        background = Image.new("RGBA", image.size, BACKGROUND)
        save_png(Image.alpha_composite(background, image).convert("RGB"),
                 "contact-sheet.png")
        save_png(sprite_frame(states["idle"]["row"], 0), "idle.png")

        tile_width, tile_height = width + 64, height + 48
        overview = Image.new("RGB", (tile_width * 3, tile_height * 3), BACKGROUND)
        for index, state in enumerate(metadata["states"]):
            name = state["name"]
            frame = state_frames[name][REPRESENTATIVE_FRAMES[name]]
            tile = labeled_frame(frame, STATE_LABELS[name])
            overview.paste(tile, ((index % 3) * tile_width, (index // 3) * tile_height))
        save_png(overview, "overview.png")

        stills = Image.new("RGB", (tile_width * 4, tile_height), BACKGROUND)
        for index, name in enumerate(("idle", "waving", "jumping", "running")):
            frame = state_frames[name][REPRESENTATIVE_FRAMES[name]]
            label = "Jump peak" if name == "jumping" else STATE_LABELS[name]
            stills.paste(labeled_frame(frame, label), (index * tile_width, 0))
        save_png(stills, "motion-stills.png")

    print(json.dumps({"gifs": gif_count, "contact_sheet": "contact-sheet.png",
                      "duration_ms": args.duration, "source": str(source),
                      "output": str(args.output), "files": generated_files}))


if __name__ == "__main__":
    main()
