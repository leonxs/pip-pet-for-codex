'use strict';

// All coordinates are in the original 768 x 768 reference space. These are
// transforms of the supplied artwork, never instructions to redraw its parts.
// Rotation is positive clockwise. left/right refer to the image, not anatomy.
// Intended hierarchy: articulated parts first, then the common body transform.
// Body scale pivot is (384, 410); the unscaled sole baseline is y = 718.
const NEUTRAL = Object.freeze({
  bodyRotate: 0, bodyScaleX: 1, bodyScaleY: 1, bodyY: 0,
  headRotate: 0, gazeX: 0, gazeY: 0, blink: 0,
  leftArmRotate: 0, rightArmRotate: 0,
  leftArmX: 0, leftArmY: 0, rightArmX: 0, rightArmY: 0,
  leftFootX: 0, leftFootY: 0, rightFootX: 0, rightFootY: 0,
  leftFootRotate: 0, rightFootRotate: 0, scarfRotate: 0,
});

const pose = (values = {}) => ({ ...NEUTRAL, ...values });

// Cancel vertical scale displacement at the sole baseline for grounded poses.
// Rotated planted feet may still need a renderer floor constraint; do not fit
// individual frames to their own bounds, which would change the character size.
const grounded = (values = {}) => pose({
  bodyY: Number(((1 - (values.bodyScaleY ?? 1)) * 308).toFixed(3)),
  ...values,
});

const states = [
  {
    name: 'idle',
    frames: [
      pose(), // Exact neutral source image: useful as the static model as well.
      grounded({ bodyScaleY: 1.003, leftArmRotate: 0.6, rightArmRotate: -0.6 }),
      grounded({ bodyScaleY: 1.005, leftArmRotate: 1, rightArmRotate: -1, scarfRotate: 0.5 }),
      grounded({ bodyScaleY: 1.003, leftArmRotate: 0.6, rightArmRotate: -0.6, blink: 0.9 }),
      grounded({ bodyScaleY: 0.998, blink: 0.12, scarfRotate: -0.4 }),
      grounded({ bodyScaleY: 0.997, leftArmRotate: -0.5, rightArmRotate: 0.5 }),
    ],
  },
  {
    name: 'running-right',
    frames: [
      pose({ bodyRotate: 3.2, gazeX: 6, gazeY: -1, leftArmRotate: -18, rightArmRotate: -7, leftFootX: 17, rightFootX: -14, leftFootRotate: -10, rightFootRotate: 10, rightFootY: -7, scarfRotate: -3.5 }),
      grounded({ bodyRotate: 4.2, bodyScaleX: 1.009, bodyScaleY: 0.992, gazeX: 6, leftArmRotate: -12, rightArmRotate: 5, leftFootX: 10, rightFootX: -7, rightFootY: -11, leftFootRotate: -3, rightFootRotate: 15, scarfRotate: -5 }),
      pose({ bodyRotate: 3.7, bodyY: -3, gazeX: 6, leftArmRotate: 1, rightArmRotate: 15, leftFootX: -2, rightFootX: 5, leftFootY: 3, rightFootY: -12, leftFootRotate: 3, rightFootRotate: 12, scarfRotate: -2.5 }),
      pose({ bodyRotate: 2.6, bodyY: -5, gazeX: 6, gazeY: -1, leftArmRotate: 12, rightArmRotate: 12, leftFootX: -12, rightFootX: 15, leftFootY: -5, rightFootY: 5, leftFootRotate: 10, rightFootRotate: -8, scarfRotate: 1 }),
      pose({ bodyRotate: 3.2, gazeX: 6, gazeY: -1, leftArmRotate: 17, rightArmRotate: 5, leftFootX: -14, rightFootX: 17, leftFootY: -7, leftFootRotate: 10, rightFootRotate: -10, scarfRotate: 3.5 }),
      grounded({ bodyRotate: 4.2, bodyScaleX: 1.009, bodyScaleY: 0.992, gazeX: 6, leftArmRotate: 9, rightArmRotate: -6, leftFootX: -7, rightFootX: 10, leftFootY: -11, leftFootRotate: 15, rightFootRotate: -3, scarfRotate: 5 }),
      pose({ bodyRotate: 3.7, bodyY: -3, gazeX: 6, leftArmRotate: -2, rightArmRotate: -16, leftFootX: 5, rightFootX: -2, leftFootY: -12, rightFootY: 3, leftFootRotate: 12, rightFootRotate: 3, scarfRotate: 2.5 }),
      pose({ bodyRotate: 2.6, bodyY: -5, gazeX: 6, gazeY: -1, leftArmRotate: -13, rightArmRotate: -13, leftFootX: 15, rightFootX: -12, leftFootY: 5, rightFootY: -5, leftFootRotate: -8, rightFootRotate: 10, scarfRotate: -1 }),
    ],
  },
  {
    name: 'running-left',
    // Separate transforms preserve the reference's asymmetric scarf placement.
    // They never mirror any source pixels or swap the physical artwork layers.
    frames: [
      pose({ bodyRotate: -3.2, gazeX: -6, gazeY: -1, leftArmRotate: 7, rightArmRotate: 18, leftFootX: 14, rightFootX: -17, leftFootY: -7, leftFootRotate: -10, rightFootRotate: 10, scarfRotate: 3.5 }),
      grounded({ bodyRotate: -4.2, bodyScaleX: 1.009, bodyScaleY: 0.992, gazeX: -6, leftArmRotate: -5, rightArmRotate: 12, leftFootX: 7, rightFootX: -10, leftFootY: -11, leftFootRotate: -15, rightFootRotate: 3, scarfRotate: 5 }),
      pose({ bodyRotate: -3.7, bodyY: -3, gazeX: -6, leftArmRotate: -15, rightArmRotate: -1, leftFootX: -5, rightFootX: 2, leftFootY: -12, rightFootY: 3, leftFootRotate: -12, rightFootRotate: -3, scarfRotate: 2.5 }),
      pose({ bodyRotate: -2.6, bodyY: -5, gazeX: -6, gazeY: -1, leftArmRotate: -12, rightArmRotate: -12, leftFootX: -15, rightFootX: 12, leftFootY: 5, rightFootY: -5, leftFootRotate: 8, rightFootRotate: -10, scarfRotate: -1 }),
      pose({ bodyRotate: -3.2, gazeX: -6, gazeY: -1, leftArmRotate: -5, rightArmRotate: -17, leftFootX: -17, rightFootX: 14, rightFootY: -7, leftFootRotate: 10, rightFootRotate: -10, scarfRotate: -3.5 }),
      grounded({ bodyRotate: -4.2, bodyScaleX: 1.009, bodyScaleY: 0.992, gazeX: -6, leftArmRotate: 6, rightArmRotate: -9, leftFootX: -10, rightFootX: 7, rightFootY: -11, leftFootRotate: 3, rightFootRotate: -15, scarfRotate: -5 }),
      pose({ bodyRotate: -3.7, bodyY: -3, gazeX: -6, leftArmRotate: 16, rightArmRotate: 2, leftFootX: 2, rightFootX: -5, leftFootY: 3, rightFootY: -12, leftFootRotate: -3, rightFootRotate: -12, scarfRotate: -2.5 }),
      pose({ bodyRotate: -2.6, bodyY: -5, gazeX: -6, gazeY: -1, leftArmRotate: 13, rightArmRotate: 13, leftFootX: 12, rightFootX: -15, leftFootY: -5, rightFootY: 5, leftFootRotate: -10, rightFootRotate: 8, scarfRotate: 1 }),
    ],
  },
  {
    name: 'waving',
    // Raise the long flipper steeply instead of stretching it horizontally.
    // Small inward shoulder offsets keep the source-tip arc inside x = 755
    // while retaining overlap with the torso at the root of the flipper.
    frames: [
      pose({ bodyRotate: -0.9, headRotate: 1.4, gazeX: 3, gazeY: -2, leftArmRotate: 4, rightArmRotate: -135, rightArmX: -18, scarfRotate: 1 }),
      pose({ bodyRotate: -1.2, headRotate: 1.8, gazeX: 4, gazeY: -3, leftArmRotate: 5, rightArmRotate: -145, rightArmX: -15, scarfRotate: 1.3 }),
      pose({ bodyRotate: -1.4, headRotate: 2, gazeX: 4, gazeY: -3, leftArmRotate: 6, rightArmRotate: -155, rightArmX: -10, scarfRotate: 1.5 }),
      pose({ bodyRotate: -1.2, headRotate: 1.8, gazeX: 4, gazeY: -3, leftArmRotate: 5, rightArmRotate: -145, rightArmX: -15, scarfRotate: 1.3 }),
    ],
  },
  {
    name: 'jumping',
    frames: [
      grounded({ bodyScaleX: 1.045, bodyScaleY: 0.94, gazeY: 2, leftArmRotate: -8, rightArmRotate: 8, leftFootX: -7, rightFootX: 7, scarfRotate: -2 }),
      pose({ bodyScaleX: 0.99, bodyScaleY: 1.025, bodyY: -34, gazeY: -5, leftArmRotate: 12, rightArmRotate: -12, leftFootX: -10, rightFootX: 10, leftFootY: -4, rightFootY: -4, leftFootRotate: -12, rightFootRotate: 12, scarfRotate: -5 }),
      pose({ bodyScaleX: 1.005, bodyScaleY: 1.01, bodyY: -85, gazeY: -5, leftArmRotate: 17, rightArmRotate: -17, leftFootX: -13, rightFootX: 13, leftFootY: -6, rightFootY: -6, leftFootRotate: -17, rightFootRotate: 17, scarfRotate: -2 }),
      pose({ bodyScaleX: 0.997, bodyScaleY: 1.012, bodyY: -36, gazeY: 3, leftArmRotate: 14, rightArmRotate: -14, leftFootX: -10, rightFootX: 10, leftFootRotate: -8, rightFootRotate: 8, scarfRotate: 5 }),
      grounded({ bodyScaleX: 1.025, bodyScaleY: 0.975, gazeY: 2, blink: 0.25, leftArmRotate: 5, rightArmRotate: -5, leftFootX: -7, rightFootX: 7, scarfRotate: 2 }),
    ],
  },
  {
    name: 'failed',
    // A tiny deflation and slow head shake communicate disappointment without
    // introducing brows, tears, symbols, or facial artwork absent in the source.
    frames: [
      pose({ gazeY: 2, blink: 0.12 }),
      grounded({ bodyScaleX: 1.012, bodyScaleY: 0.982, headRotate: -2, gazeX: -2, gazeY: 5, blink: 0.4, leftArmRotate: -5, rightArmRotate: 5, scarfRotate: -1 }),
      grounded({ bodyScaleX: 1.019, bodyScaleY: 0.97, headRotate: -3.8, gazeX: -4, gazeY: 6, blink: 0.72, leftArmRotate: -8, rightArmRotate: 8, scarfRotate: -2 }),
      grounded({ bodyScaleX: 1.019, bodyScaleY: 0.97, headRotate: -1.5, gazeX: -2, gazeY: 6, blink: 0.85, leftArmRotate: -8, rightArmRotate: 8, scarfRotate: -1 }),
      grounded({ bodyScaleX: 1.019, bodyScaleY: 0.97, headRotate: 3, gazeX: 4, gazeY: 6, blink: 0.7, leftArmRotate: -8, rightArmRotate: 8, scarfRotate: 1.5 }),
      grounded({ bodyScaleX: 1.015, bodyScaleY: 0.977, headRotate: 1.5, gazeX: 2, gazeY: 5, blink: 0.45, leftArmRotate: -6, rightArmRotate: 6, scarfRotate: 1 }),
      grounded({ bodyScaleX: 1.008, bodyScaleY: 0.988, headRotate: -0.8, gazeY: 4, blink: 0.22, leftArmRotate: -3, rightArmRotate: 3, scarfRotate: -0.5 }),
      grounded({ bodyScaleX: 1.002, bodyScaleY: 0.996, gazeY: 2, blink: 0.08, leftArmRotate: -1, rightArmRotate: 1 }),
    ],
  },
  {
    name: 'waiting',
    frames: [
      pose({ gazeX: -3, headRotate: -0.6 }),
      grounded({ bodyScaleY: 1.003, gazeX: -6, gazeY: -1, headRotate: -1.2, leftArmRotate: 1, rightArmRotate: -1 }),
      pose({ gazeY: -2, blink: 0.85, scarfRotate: 0.5 }),
      grounded({ bodyScaleY: 0.998, gazeX: 6, gazeY: -1, headRotate: 1.2, rightFootY: -7, rightFootRotate: -7, leftArmRotate: -1, rightArmRotate: 1 }),
      pose({ gazeX: 5, headRotate: 0.8, rightFootY: -2, rightFootRotate: -2, scarfRotate: -0.5 }),
      pose({ gazeX: 1, gazeY: 1, headRotate: 0.2 }),
    ],
  },
  {
    name: 'running',
    // The Work activity uses inward fingertip taps; it is distinct from travel.
    frames: [
      pose({ gazeY: 4, headRotate: -0.6, leftArmRotate: -24, rightArmRotate: 25 }),
      grounded({ bodyScaleY: 0.997, gazeX: -1, gazeY: 5, headRotate: -1, leftArmRotate: -36, rightArmRotate: 29, scarfRotate: -0.8 }),
      grounded({ bodyScaleY: 1.002, gazeX: -1, gazeY: 5, headRotate: -0.4, leftArmRotate: -30, rightArmRotate: 35, scarfRotate: -0.3 }),
      pose({ gazeX: 1, gazeY: 4, headRotate: 0.6, leftArmRotate: -24, rightArmRotate: 28, blink: 0.15 }),
      grounded({ bodyScaleY: 0.997, gazeX: 1, gazeY: 5, headRotate: 1, leftArmRotate: -29, rightArmRotate: 36, scarfRotate: 0.8 }),
      grounded({ bodyScaleY: 1.002, gazeY: 4, headRotate: 0.3, leftArmRotate: -34, rightArmRotate: 30, scarfRotate: 0.3 }),
    ],
  },
  {
    name: 'review',
    // These angles control the thinking gesture along the renderer's curved
    // elbow path: keep the shoulder below the scarf, then bring the tip around
    // the scarf's outer edge to the beak without folding through the red band.
    frames: [
      pose({ headRotate: -1, gazeX: 3, gazeY: -3, leftArmRotate: -8, rightArmRotate: 96 }),
      grounded({ bodyScaleY: 1.002, headRotate: -2, gazeX: 4, gazeY: -5, leftArmRotate: -10, rightArmRotate: 115, scarfRotate: 0.5 }),
      grounded({ bodyScaleY: 1.003, headRotate: -2.7, gazeX: 4, gazeY: -6, leftArmRotate: -11, rightArmRotate: 122, scarfRotate: 0.8 }),
      grounded({ bodyScaleY: 1.001, headRotate: -2.5, gazeX: 3, gazeY: -5, leftArmRotate: -11, rightArmRotate: 119, blink: 0.4, scarfRotate: 0.5 }),
      pose({ headRotate: -1.8, gazeX: 2, gazeY: -4, leftArmRotate: -10, rightArmRotate: 115 }),
      pose({ headRotate: -1.2, gazeX: 2, gazeY: -3, leftArmRotate: -8, rightArmRotate: 103, scarfRotate: -0.3 }),
    ],
  },
];

// Clockwise compass order: 0 = up, 4 = right, 8 = down, 12 = left.
const looks = Array.from({ length: 16 }, (_, index) => {
  const angle = index * Math.PI / 8;
  const x = Math.sin(angle);
  const y = -Math.cos(angle);
  return pose({
    gazeX: Number((x * 6).toFixed(3)),
    gazeY: Number((y * 6).toFixed(3)),
    headRotate: Number((x * 1.2).toFixed(3)),
  });
});

module.exports = { states, looks };
