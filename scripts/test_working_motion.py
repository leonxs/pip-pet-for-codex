"""Check that the encoded work loop stays readable at a small pet size."""

import argparse
from collections import deque
from pathlib import Path
import unittest

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--input", type=Path, default=ROOT / "assets" / "spritesheet.png")
options, test_args = parser.parse_known_args()


class WorkingMotionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Image.open(options.input) as atlas:
            cls.frames = [atlas.crop((column * 192, 7 * 208,
                                      (column + 1) * 192, 8 * 208)).convert("RGBA")
                          for column in range(6)]
        cls.small = [frame.resize((96, 104)) for frame in cls.frames]

    def test_motion_survives_small_overlay_including_loop_seam(self):
        for index, frame in enumerate(self.small):
            following = self.small[(index + 1) % len(self.small)]
            difference = ImageChops.difference(frame, following)
            visible = ImageChops.lighter(
                ImageChops.lighter(difference.getchannel("R"),
                                  difference.getchannel("G")),
                difference.getchannel("B"))
            changed = sum(visible.histogram()[24:])
            with self.subTest(frame=index):
                self.assertGreaterEqual(changed, 300,
                                        "Work motion is too subtle at half size.")

    def test_both_flippers_move_and_soles_stay_planted(self):
        edges, soles = [], []
        for frame in self.small:
            alpha = frame.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
            bounds = alpha.crop((0, 55, 96, 84)).getbbox()
            edges.append((bounds[0], bounds[2]))
            feet = [y for y in range(75, 104) for x in range(96)
                    if self.is_foot(frame.getpixel((x, y)))]
            self.assertTrue(feet, "Work frame lost its feet.")
            soles.append(max(feet))
        for side in range(2):
            positions = [edge[side] for edge in edges]
            self.assertGreaterEqual(max(positions) - min(positions), 4,
                                    "Both outward flipper sweeps must remain visible.")
        self.assertLessEqual(max(soles) - min(soles), 1,
                             "The work cycle should keep the feet on the ground.")

    @staticmethod
    def is_foot(pixel):
        red, green, blue, alpha = pixel
        return alpha > 128 and red > 150 and 75 < green < red * .9 and blue < green * .9

    def test_no_detached_limb_or_scarf_fragments(self):
        for index, frame in enumerate(self.frames):
            width, height = frame.size
            alpha = frame.getchannel("A").tobytes()
            remaining = {point for point, value in enumerate(alpha) if value >= 32}
            components = []
            while remaining:
                queue = deque([remaining.pop()])
                count = 0
                while queue:
                    point = queue.popleft()
                    count += 1
                    x, y = point % width, point // width
                    neighbors = []
                    if x: neighbors.append(point - 1)
                    if x + 1 < width: neighbors.append(point + 1)
                    if y: neighbors.append(point - width)
                    if y + 1 < height: neighbors.append(point + width)
                    for neighbor in neighbors:
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            queue.append(neighbor)
                if count >= 8:
                    components.append(count)
            with self.subTest(frame=index):
                self.assertEqual(len(components), 1,
                                 "The work pose contains a detached visible fragment.")


if __name__ == "__main__":
    unittest.main(argv=[__file__, *test_args])
