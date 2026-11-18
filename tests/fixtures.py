"""Synthetic 21-point hands (MediaPipe indices), fingers pointing up, wrist at bottom."""
import math

WRIST = (0.5, 0.8)
MCP_X = {"index": 0.44, "middle": 0.48, "ring": 0.52, "pinky": 0.56}


def make_hand(extended):
    pts = [WRIST, (0.42, 0.75), (0.38, 0.70), (0.35, 0.65),
           (0.32, 0.60) if "thumb" in extended else (0.46, 0.66)]
    for f, x in MCP_X.items():
        ys = (0.60, 0.52, 0.47, 0.42) if f in extended else (0.60, 0.52, 0.56, 0.62)
        pts += [(x, y) for y in ys]
    return pts


def open_palm():   return make_hand({"thumb", "index", "middle", "ring", "pinky"})
def fist():        return make_hand(set())
def point_index(): return make_hand({"index"})
def scroll_pose(): return make_hand({"index", "middle"})


def pinch(ratio):
    """Index pointing, thumb tip placed so pinch_ratio == ratio."""
    lm = point_index()
    size = math.dist(lm[0], lm[9])
    tx, ty = lm[8]
    lm[4] = (tx - ratio * size, ty)
    return lm


def scale(lm, s):
    wx, wy = lm[0]
    return [(wx + (x - wx) * s, wy + (y - wy) * s) for x, y in lm]


def shift(lm, dx, dy):
    return [(x + dx, y + dy) for x, y in lm]


def call_pose():   return make_hand({"thumb", "pinky"})


def ok_sign():
    """Thumb and index touching, other three fingers up (a common way to pinch)."""
    lm = make_hand({"thumb", "index", "middle", "ring", "pinky"})
    lm[4] = (lm[8][0] - 0.01, lm[8][1])
    return lm
