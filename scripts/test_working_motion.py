"""Check readable work motion and folded resting poses in the encoded atlas."""

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
        changes = []
        for index, frame in enumerate(self.small):
            following = self.small[(index + 1) % len(self.small)]
            difference = ImageChops.difference(frame, following)
            visible = ImageChops.lighter(
                ImageChops.lighter(difference.getchannel("R"),
                                  difference.getchannel("G")),
                difference.getchannel("B"))
            changed = sum(visible.histogram()[24:])
            changes.append(changed)
            with self.subTest(frame=index):
                self.assertGreaterEqual(changed, 100,
                                        "Work frame or its loop seam is static at half size.")
        self.assertGreaterEqual(sum(changes) / len(changes), 350,
                                "The overall work cycle is too subtle at half size.")
        self.assertGreaterEqual(max(changes), 500,
                                "The work cycle needs a readable active gesture.")

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


class RestingPoseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with Image.open(options.input) as atlas:
            cls.resting = []
            cls.idle = []
            for row, columns in ((0, range(6)), (9, range(8)),
                                 (10, range(8)), (7, (0, 5))):
                for column in columns:
                    frame = atlas.crop((column * 192, row * 208,
                                        (column + 1) * 192, (row + 1) * 208)).convert("RGBA")
                    cls.resting.append((row, column, frame.resize((96, 104))))
                    if row == 0:
                        cls.idle.append(frame)

    def test_idle_gaze_and_work_endpoints_keep_flippers_tucked(self):
        for row, column, frame in self.resting:
            alpha = frame.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
            bounds = alpha.crop((0, 55, 96, 84)).getbbox()
            with self.subTest(row=row, column=column):
                self.assertIsNotNone(bounds)
                self.assertGreaterEqual(bounds[0], 10, "Left flipper opens during rest.")
                self.assertLessEqual(bounds[2], 85, "Right flipper opens during rest.")

    def test_idle_keeps_breathing_and_blinking_without_foot_drift(self):
        self.assertGreaterEqual(len({frame.tobytes() for frame in self.idle}), 4,
                                "Folded idle should remain visibly alive.")
        soles = []
        for original in self.idle:
            frame = original.resize((96, 104))
            feet = [y for y in range(75, 104) for x in range(96)
                    if WorkingMotionChecks.is_foot(frame.getpixel((x, y)))]
            self.assertTrue(feet)
            soles.append(max(feet))
        self.assertLessEqual(max(soles) - min(soles), 1)


if __name__ == "__main__":
    unittest.main(argv=[__file__, *test_args])
