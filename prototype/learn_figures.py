"""Illustrations for the web app's Learn pages (web/public/figures/learn/*.jpg).

Takes one analyzed session (the videos plus the keypoints JSON the worker writes for the browser)
and renders, for each Metric, a frame at the gait event the Metric refers to with the relevant body
segments and angle highlighted, in the same visual language as the web player.

    uv run python learn_figures.py --side-video side.mp4 --side-keypoints keypoints_side.json \\
        --rear-video rear.mp4 --rear-keypoints keypoints_rear.json --height-cm 179 \\
        --out ../web/public/figures/learn --manifest ../web/src/content/learn-figures.json

The runner's face is blurred in every side-view frame: the pages are public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from analyze import LEG_LENGTH_RATIO

COLOR = {"L": (255, 200, 0), "R": (0, 120, 255), "C": (255, 79, 163)}
WHITE = (255, 255, 255)
BONES = [("shoulder", "hip"), ("hip", "knee"), ("knee", "ankle"), ("ankle", "heel"), ("heel", "toe"), ("ankle", "toe")]
PANEL_W = 720  # output width of one panel, px
SS = 2  # supersampling factor for anti-aliased drawing
FONT = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
FONT_REGULAR = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans"))


@dataclass
class Clip:
    path: Path
    joints: list[str]
    frames: np.ndarray  # (rows, joints, 3) filtered points + score
    start: int
    step: int
    events: dict
    src_fps: float = 240.0  # real frames per second of the file (capture fps for slow motion)

    def row(self, file_frame: int) -> np.ndarray:
        return self.frames[(file_frame - self.start) // self.step]

    def p(self, file_frame: int, name: str) -> np.ndarray:
        return self.row(file_frame)[self.joints.index(name), :2].astype(float)


def load(video: Path, keypoints: Path) -> Clip:
    d = json.loads(keypoints.read_text())
    return Clip(video, d["joints"], np.array(d["frames"], dtype=float), d["start_frame"], d["frame_step"], d["events"], d["fps"] * d["frame_step"])


def read_frames(path: Path, wanted: set[int]) -> dict[int, np.ndarray]:
    """Sequential decode, so frame numbers match the worker's (which also reads sequentially)."""
    cap = cv2.VideoCapture(str(path))
    out, i, last = {}, 0, max(wanted)
    while i <= last:
        ok, f = cap.read()
        if not ok:
            break
        if i in wanted:
            out[i] = f
        i += 1
    cap.release()
    return out


# ---------------------------------------------------------------- drawing


class Panel:
    """One cropped frame, drawn at SS× and downsampled. Coordinates passed in are video pixels."""

    def __init__(self, frame_bgr: np.ndarray, box: tuple[float, float, float, float], width: int = PANEL_W):
        x0, y0, x1, y1 = (int(round(v)) for v in box)
        h, w = frame_bgr.shape[:2]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        self.x0, self.y0 = x0, y0
        crop = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
        self.out_w = width
        self.out_h = int(round(width * (y1 - y0) / (x1 - x0)))
        self.s = width * SS / (x1 - x0)
        self.img = Image.fromarray(crop).resize((width * SS, self.out_h * SS), Image.LANCZOS).convert("RGBA")
        self.overlay = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.overlay)
        # Drawing unit, fixed in output pixels (~3 px) whatever the panel width: narrow panels of a
        # multi-panel figure must not get smaller labels, since the whole figure is scaled down on a phone.
        self.u = PANEL_W * SS / 240

    def xy(self, p) -> tuple[float, float]:
        return ((p[0] - self.x0) * self.s, (p[1] - self.y0) * self.s)

    def spotlight(self, centres, radius_px: float, dim: float = 0.5):
        """Darken everything except soft discs around the points the figure is about."""
        mask = Image.new("L", self.img.size, 0)
        md = ImageDraw.Draw(mask)
        r = radius_px * self.s
        for c in centres:
            x, y = self.xy(c)
            md.ellipse((x - r, y - r, x + r, y + r), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(r * 0.35))
        dark = Image.new("RGBA", self.img.size, (0, 0, 0, int(255 * dim)))
        shaded = Image.alpha_composite(self.img, dark)
        self.img = Image.composite(self.img, shaded, mask)

    def skeleton(self, clip: Clip, frame: int, alpha: int = 150, width: float = 1.0):
        for side in ("L", "R"):
            for a, b in BONES:
                pa, pb = clip.p(frame, f"{a}_{side}"), clip.p(frame, f"{b}_{side}")
                self.draw.line([self.xy(pa), self.xy(pb)], fill=COLOR[side] + (alpha,), width=int(self.u * width))

    def segment(self, a, b, color, width: float = 2.2):
        self.draw.line([self.xy(a), self.xy(b)], fill=WHITE + (255,), width=int(self.u * (width + 1.2)))
        self.draw.line([self.xy(a), self.xy(b)], fill=color + (255,), width=int(self.u * width))
        for p in (a, b):
            x, y = self.xy(p)
            r = self.u * width * 1.4
            self.draw.ellipse((x - r, y - r, x + r, y + r), fill=color + (255,), outline=WHITE + (255,), width=int(self.u * 0.6))

    def dashed(self, a, b, color=WHITE, width: float = 1.3, dash: float = 5):
        (x0, y0), (x1, y1) = self.xy(a), self.xy(b)
        length = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(length / (dash * self.u)))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1, (i + 1) / n)
            self.draw.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0), (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)], fill=color + (235,), width=int(self.u * width))

    def angle(self, centre, ref_dir: float, seg_dir: float, color, text: str, radius: float = 16, ref_len: float = 2.2):
        """Wedge from the reference direction to the segment direction (radians, image coords), with
        a dashed reference line and a value chip on the bisector."""
        cx, cy = self.xy(centre)
        r = radius * self.u
        ex = (centre[0] + math.cos(ref_dir) * r * ref_len / self.s, centre[1] + math.sin(ref_dir) * r * ref_len / self.s)
        self.dashed(centre, ex)
        delta = (seg_dir - ref_dir + math.pi) % (2 * math.pi) - math.pi
        a0, a1 = (ref_dir, ref_dir + delta) if delta >= 0 else (ref_dir + delta, ref_dir)
        box = (cx - r, cy - r, cx + r, cy + r)
        self.draw.pieslice(box, math.degrees(a0), math.degrees(a1), fill=color + (130,))
        self.draw.arc(box, math.degrees(a0), math.degrees(a1), fill=color + (255,), width=int(self.u * 1.6))
        mid = ref_dir + delta / 2
        self.chip((cx + math.cos(mid) * (r + 9 * self.u), cy + math.sin(mid) * (r + 9 * self.u)), text, color, canvas=True)

    def chip(self, pos, text: str, color, canvas: bool = False, size: float = 10.5):
        x, y = pos if canvas else self.xy(pos)
        font = ImageFont.truetype(FONT, int(size * self.u))
        l, t, r, b = self.draw.textbbox((0, 0), text, font=font)
        w, h = r - l + size * self.u * 0.9, (b - t) + size * self.u * 0.8
        self.draw.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=h / 2, fill=(15, 15, 20, 225), outline=color + (255,), width=int(self.u * 0.6))
        self.draw.text((x, y), text, font=font, fill=WHITE + (255,), anchor="mm")

    def tag(self, text: str, corner: str = "tl"):
        font = ImageFont.truetype(FONT, int(9.5 * self.u))
        l, t, r, b = self.draw.textbbox((0, 0), text, font=font)
        w, h = r - l + 8 * self.u, b - t + 6 * self.u
        m = 6 * self.u
        x = m if corner[1] == "l" else self.img.size[0] - m - w
        y = m if corner[0] == "t" else self.img.size[1] - m - h
        self.draw.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=(15, 15, 20, 215))
        self.draw.text((x + w / 2, y + h / 2), text, font=font, fill=WHITE + (255,), anchor="mm")

    def arrow(self, a, b, color, width: float = 1.2):
        (x0, y0), (x1, y1) = self.xy(a), self.xy(b)
        self.draw.line([(x0, y0), (x1, y1)], fill=color + (255,), width=int(self.u * width))
        for (xa, ya), (xb, yb) in (((x0, y0), (x1, y1)), ((x1, y1), (x0, y0))):
            ang = math.atan2(yb - ya, xb - xa)
            hl = 5 * self.u
            pts = [(xb, yb), (xb - hl * math.cos(ang - 0.45), yb - hl * math.sin(ang - 0.45)), (xb - hl * math.cos(ang + 0.45), yb - hl * math.sin(ang + 0.45))]
            self.draw.polygon(pts, fill=color + (255,))

    def image(self) -> Image.Image:
        out = Image.alpha_composite(self.img, self.overlay).convert("RGB")
        return out.resize((self.out_w, self.out_h), Image.LANCZOS)


def blur_face(frame: np.ndarray, clip: Clip, f: int) -> np.ndarray:
    """Blur the whole head: a disc sized from the nose-to-shoulders distance, centred a little behind
    the nose (the nose keypoint is at the front of the face). The work region extends past the disc's
    soft edge, so the blur fades out instead of ending on a straight cut."""
    nose = clip.p(f, "nose")
    sh = (clip.p(f, "shoulder_L") + clip.p(f, "shoulder_R")) / 2
    hip = (clip.p(f, "hip_L") + clip.p(f, "hip_R")) / 2
    dist = float(np.linalg.norm(nose - sh))
    facing = 1 if nose[0] >= hip[0] else -1
    r = int(0.95 * dist)
    cx, cy = int(nose[0] - facing * 0.35 * r), int(nose[1] - 0.1 * r)
    soft = max(2, r // 5)
    m = r + 3 * soft
    out = frame.copy()
    x0, y0, x1, y1 = max(0, cx - m), max(0, cy - m), min(frame.shape[1], cx + m), min(frame.shape[0], cy + m)
    if x1 <= x0 or y1 <= y0:
        return out
    region = out[y0:y1, x0:x1].astype(np.float32)
    blurred = cv2.GaussianBlur(region, (0, 0), r / 2.5)
    mask = np.zeros(region.shape[:2], np.float32)
    cv2.circle(mask, (cx - x0, cy - y0), r, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), soft)[..., None]
    out[y0:y1, x0:x1] = (blurred * mask + region * (1 - mask)).astype(np.uint8)
    return out


def grid(images: list[Image.Image], cols: int, gap: int = 8) -> Image.Image:
    rows = [hstack(images[i:i + cols], gap) for i in range(0, len(images), cols)]
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + gap * (len(rows) - 1)), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + gap
    return out


def hstack(images: list[Image.Image], gap: int = 8) -> Image.Image:
    h = max(i.height for i in images)
    out = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), h), (255, 255, 255))
    x = 0
    for i in images:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


SAVED: dict[str, dict] = {}


def save(img: Image.Image, out: Path, name: str):
    path = out / f"{name}.jpg"
    img.save(path, quality=84, optimize=True, progressive=True)
    # The content hash goes into the image URL, so caches drop the old version when a figure changes.
    SAVED[name] = {"width": img.width, "height": img.height, "version": hashlib.sha1(path.read_bytes()).hexdigest()[:10]}
    print(f"  {name}.jpg  {img.width}x{img.height}")


# ---------------------------------------------------------------- geometry


def direction(clip: Clip) -> int:
    j = clip.joints.index
    hip = (clip.frames[:, j("hip_L"), 0] + clip.frames[:, j("hip_R"), 0]) / 2
    return 1 if np.nanmean(clip.frames[:, j("nose"), 0] - hip) >= 0 else -1


def signed(v: float) -> str:
    r = round(v)
    return f"{r:+d}°" if r else "0°"


def ang(a, b) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def box_around(points, pad_x: float, pad_y: float, aspect: float | None = None) -> tuple[float, float, float, float]:
    pts = np.array(points)
    x0, y0 = pts.min(0)
    x1, y1 = pts.max(0)
    x0, x1, y0, y1 = x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y
    if aspect:  # width / height
        cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        if w / h < aspect:
            w = h * aspect
        else:
            h = w / aspect
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return x0, y0, x1, y1


# ---------------------------------------------------------------- figures


def side_figures(clip: Clip, out: Path, height_cm: float):
    d = direction(clip)
    near = "L"
    ic = np.array(clip.events["ic"][near])
    to = np.array(clip.events["to"][near])
    ic_other = np.array(clip.events["ic"]["R" if near == "L" else "L"])
    # A cycle in the middle of the window, with toe-off and the other foot's contact inside it.
    k = len(ic) // 2
    f_ic, f_next = int(ic[k]), int(ic[k + 1])
    f_to = int(to[(to > f_ic) & (to < f_next)][0])
    f_mid = (f_ic + f_to) // 2
    f_other = int(ic_other[(ic_other > f_to) & (ic_other < f_next)][0])
    f_swing = (f_to + f_next) // 2
    hip_mid = lambda f: (clip.p(f, "hip_L") + clip.p(f, "hip_R")) / 2  # noqa: E731
    sh_mid = lambda f: (clip.p(f, "shoulder_L") + clip.p(f, "shoulder_R")) / 2  # noqa: E731
    leg_px = max(np.median(np.linalg.norm(clip.frames[:, clip.joints.index(f"hip_{s}"), :2] - clip.frames[:, clip.joints.index(f"knee_{s}"), :2], axis=1)
                           + np.linalg.norm(clip.frames[:, clip.joints.index(f"knee_{s}"), :2] - clip.frames[:, clip.joints.index(f"ankle_{s}"), :2], axis=1)) for s in "LR")
    cm_per_px = height_cm * LEG_LENGTH_RATIO / leg_px
    # Vertical oscillation: the head's highest and lowest point over this cycle (the app measures the
    # head; the hip points follow the thighs).
    head = lambda f: clip.p(f, "nose")  # noqa: E731
    head_y = np.array([head(f)[1] for f in range(f_ic, f_next, clip.step)])
    f_low = f_ic + int(np.argmax(head_y)) * clip.step
    f_high = f_ic + int(np.argmin(head_y)) * clip.step

    frames = read_frames(clip.path, {f_ic, f_to, f_mid, f_other, f_swing, f_low, f_high})
    frames = {f: blur_face(img, clip, f) for f, img in frames.items()}
    P = lambda f, n: clip.p(f, f"{n}_{near}")  # noqa: E731
    col = COLOR[near]
    leg_box = lambda f, aspect=0.8: box_around([P(f, "hip"), P(f, "knee"), P(f, "ankle"), P(f, "heel"), P(f, "toe")], 90, 70, aspect)  # noqa: E731
    print("side figures (cycle", f_ic, "->", f_next, ")")

    # Knee flexion at initial contact.
    H, K, A = P(f_ic, "hip"), P(f_ic, "knee"), P(f_ic, "ankle")
    flex = abs(math.degrees((ang(K, A) - ang(H, K) + math.pi) % (2 * math.pi) - math.pi))
    pn = Panel(frames[f_ic], leg_box(f_ic))
    pn.spotlight([K], 170)
    pn.skeleton(clip, f_ic)
    pn.segment(H, K, col)
    pn.segment(K, A, col)
    pn.angle(K, ang(H, K), ang(K, A), col, f"{flex:.0f}°", radius=42, ref_len=2.0)
    pn.tag("Initial contact")
    save(pn.image(), out, "knee-flexion")

    # Tibia angle at initial contact.
    tib = math.degrees(math.atan2(d * (K[0] - A[0]), A[1] - K[1]))
    pn = Panel(frames[f_ic], leg_box(f_ic))
    pn.spotlight([A, K], 150)
    pn.skeleton(clip, f_ic)
    pn.segment(K, A, col)
    pn.angle(A, -math.pi / 2, ang(A, K), col, signed(tib), radius=48, ref_len=2.0)
    pn.tag("Initial contact")
    save(pn.image(), out, "tibia-angle")

    # Foot angle at initial contact.
    He, T = P(f_ic, "heel"), P(f_ic, "toe")
    foot = math.degrees(math.atan2(-(T[1] - He[1]), d * (T[0] - He[0])))
    fbox = box_around([He, T, A], 150, 120, 1.25)
    pn = Panel(frames[f_ic], fbox)
    pn.spotlight([He, T], 110)
    pn.skeleton(clip, f_ic)
    pn.segment(He, T, col)
    pn.angle(He, 0.0 if d > 0 else math.pi, ang(He, T), col, signed(foot), radius=30, ref_len=3.0)
    pn.tag("Initial contact")
    save(pn.image(), out, "foot-angle")

    # Overstride: ankle ahead of the hip at initial contact.
    Hm = hip_mid(f_ic)
    over_cm = d * (A[0] - Hm[0]) * cm_per_px
    floor_y = max(He[1], T[1]) + 25
    pn = Panel(frames[f_ic], box_around([Hm, A, He, T, P(f_ic, "knee")], 110, 80, 0.8))
    pn.spotlight([Hm, A], 150)
    pn.skeleton(clip, f_ic)
    pn.dashed(Hm, (Hm[0], floor_y), width=1.1)
    pn.dashed(A, (A[0], floor_y), width=1.1)
    pn.segment(Hm, A, COLOR["C"], width=1.6)
    pn.arrow((Hm[0], floor_y), (A[0], floor_y), COLOR["C"])
    pn.chip(((Hm[0] + A[0]) / 2, floor_y + 32), f"{over_cm:.0f} cm", COLOR["C"])
    pn.tag("Initial contact")
    save(pn.image(), out, "overstride")

    # Trunk lean at midstance.
    Hm, Sm = hip_mid(f_mid), sh_mid(f_mid)
    trunk = math.degrees(math.atan2(d * (Sm[0] - Hm[0]), Hm[1] - Sm[1]))
    pn = Panel(frames[f_mid], box_around([Hm, Sm, clip.p(f_mid, "nose"), P(f_mid, "knee")], 160, 90, 0.8))
    pn.spotlight([Hm, Sm], 200)
    pn.skeleton(clip, f_mid)
    pn.segment(Hm, Sm, COLOR["C"])
    pn.angle(Hm, -math.pi / 2, ang(Hm, Sm), COLOR["C"], signed(trunk), radius=40, ref_len=2.4)
    pn.tag("Midstance")
    save(pn.image(), out, "trunk-lean")

    # Thigh angle (the "Hip" angle of the player): at contact and at toe-off.
    panels = []
    for f, label in ((f_ic, "Initial contact"), (f_to, "Toe-off")):
        H, K = P(f, "hip"), P(f, "knee")
        v = math.degrees(math.atan2(d * (K[0] - H[0]), K[1] - H[1]))
        pn = Panel(frames[f], box_around([H, K, P(f, "ankle"), hip_mid(f)], 130, 90, 0.8), width=PANEL_W // 2 + 60)
        pn.spotlight([H, K], 170)
        pn.skeleton(clip, f)
        pn.segment(H, K, col)
        pn.angle(H, math.pi / 2, ang(H, K), col, signed(v), radius=30, ref_len=2.4)
        pn.tag(label)
        panels.append(pn.image())
    save(hstack(panels), out, "thigh-angle")

    # Contact time: initial contact and toe-off of the same foot.
    ms = (f_to - f_ic) / clip.src_fps * 1000
    panels = []
    feet_box = box_around([P(f, n) for f in (f_ic, f_to) for n in ("knee", "ankle", "heel", "toe")], 110, 70, 0.85)
    for f, label in ((f_ic, "Initial contact · 0 ms"), (f_to, f"Toe-off · +{ms:.0f} ms")):
        pn = Panel(frames[f], feet_box, width=PANEL_W // 2 + 60)
        pn.spotlight([P(f, "heel"), P(f, "toe")], 140)
        pn.skeleton(clip, f)
        pn.segment(P(f, "heel"), P(f, "toe"), col)
        pn.tag(label)
        panels.append(pn.image())
    save(hstack(panels), out, "contact-time")

    # Flight time: this foot's toe-off, then the other foot's initial contact.
    other = "R" if near == "L" else "L"
    ms = (f_other - f_to) / clip.src_fps * 1000
    feet_box = box_around([clip.p(f, f"{n}_{s}") for f, s in ((f_to, near), (f_other, other)) for n in ("knee", "ankle", "heel", "toe")], 110, 70, 0.85)
    panels = []
    for f, s, label in ((f_to, near, "Toe-off · 0 ms"), (f_other, other, f"Other foot lands · +{ms:.0f} ms")):
        pn = Panel(frames[f], feet_box, width=PANEL_W // 2 + 60)
        pn.spotlight([clip.p(f, f"heel_{s}"), clip.p(f, f"toe_{s}")], 140)
        pn.skeleton(clip, f)
        pn.segment(clip.p(f, f"heel_{s}"), clip.p(f, f"toe_{s}"), COLOR[s])
        pn.tag(label)
        panels.append(pn.image())
    save(hstack(panels), out, "flight-time")

    # Cadence / step: one foot's contact, then the other foot's contact.
    step_s = (f_other - f_ic) / clip.src_fps
    feet_box = box_around([clip.p(f, f"{n}_{s}") for f, s in ((f_ic, near), (f_other, other)) for n in ("hip", "ankle", "heel", "toe")], 110, 70, 0.8)
    panels = []
    for f, s, label in ((f_ic, near, "Left foot lands · 0 s"), (f_other, other, f"Right foot lands · +{step_s:.2f} s")):
        pn = Panel(frames[f], feet_box, width=PANEL_W // 2 + 60)
        pn.spotlight([clip.p(f, f"heel_{s}"), clip.p(f, f"toe_{s}")], 140)
        pn.skeleton(clip, f)
        pn.segment(clip.p(f, f"heel_{s}"), clip.p(f, f"toe_{s}"), COLOR[s])
        pn.tag(label)
        panels.append(pn.image())
    save(hstack(panels), out, "cadence")

    # Vertical oscillation: head at its lowest (mid-stance) and highest (flight) in the cycle. The face
    # is blurred, so the marker sits on the blurred head.
    lo, hi = head(f_low), head(f_high)
    vo_cm = (lo[1] - hi[1]) * cm_per_px
    vbox = box_around([lo, hi, sh_mid(f_low), hip_mid(f_low)], 190, 120, 0.8)
    panels = []
    for f, label in ((f_high, "Head highest"), (f_low, "Head lowest")):
        pn = Panel(frames[f], vbox, width=PANEL_W // 2 + 60)
        pn.spotlight([head(f)], 170)
        pn.skeleton(clip, f)
        for y in (hi[1], lo[1]):
            pn.dashed((vbox[0] + 10, y), (vbox[2] - 10, y), width=1.0)
        x = head(f)[0] + 110
        pn.arrow((x, hi[1]), (x, lo[1]), COLOR["C"])
        c = head(f)
        pn.segment(c, c, COLOR["C"], width=2.6)
        if f == f_low:
            pn.chip((x + 80, (hi[1] + lo[1]) / 2 + 60), f"{vo_cm:.1f} cm", COLOR["C"])
        pn.tag(label)
        panels.append(pn.image())
    save(hstack(panels), out, "vertical-oscillation")

    # Gait cycle: the four phases the Metrics refer to.
    panels = []
    cbox = box_around([clip.p(f, n) for f in (f_ic, f_mid, f_to, f_swing) for n in ("hip_L", "hip_R", "ankle_L", "ankle_R", "toe_L", "toe_R", "knee_L", "knee_R")], 70, 60, 0.62)
    for f, label in ((f_ic, "1 · Initial contact"), (f_mid, "2 · Midstance"), (f_to, "3 · Toe-off"), (f_swing, "4 · Swing")):
        pn = Panel(frames[f], cbox, width=420)
        pn.spotlight([P(f, "knee"), P(f, "ankle")], 230, dim=0.35)
        pn.skeleton(clip, f, alpha=110)
        pn.segment(P(f, "hip"), P(f, "knee"), col, width=1.6)
        pn.segment(P(f, "knee"), P(f, "ankle"), col, width=1.6)
        pn.segment(P(f, "heel"), P(f, "toe"), col, width=1.6)
        pn.tag(label)
        panels.append(pn.image())
    save(grid(panels, cols=2, gap=8), out, "gait-cycle")


def rear_figures(clip: Clip, out: Path):
    import analyze_rear as rear

    j = clip.joints.index
    kp, sc = clip.frames[..., :2], clip.frames[..., 2]
    fps = clip.src_fps / clip.step
    a, b = rear.running_segment(kp, sc, fps)
    hl, hr = kp[:, j("hip_L")], kp[:, j("hip_R")]
    pelvis_raw = np.degrees(np.arctan2(hl[:, 1] - hr[:, 1], np.abs(hl[:, 0] - hr[:, 0])))
    baseline = float(np.nanmean(pelvis_raw[a:b]))
    pelvis = pelvis_raw - baseline
    left_is_left = np.nanmean(hl[a:b, 0] - hr[a:b, 0]) < 0
    medial = {"L": 1 if left_is_left else -1, "R": -1 if left_is_left else 1}
    # Stance windows recomputed on the running segment (older keypoint files lack the trimming).
    _, info, _ = rear.compute(kp[a:b], sc[a:b], fps)
    windows = [(x + a, y + a) for x, y in info["stance_windows_L"]]  # rows; the rear file starts at frame 0
    # Left foot on the belt: the right (swing-side) hip drops. Take the stance with the clearest drop,
    # at its peak, so the angle is visible in the figure.
    peaks = [(w0 + int(np.argmax(-pelvis[w0:w1])), float(np.max(-pelvis[w0:w1]))) for w0, w1 in windows if w1 > w0]
    f = max(peaks, key=lambda x: x[1])[0]
    frames = read_frames(clip.path, {f})
    img = frames[f]
    P = lambda n: kp[f, j(n)]  # noqa: E731
    HL, HR, KL = P("hip_L"), P("hip_R"), P("knee_L")
    mid = (HL + HR) / 2
    box = box_around([HL, HR, KL, P("knee_R"), P("ankle_L"), P("ankle_R")], 170, 120, 0.85)
    print("rear figures (frame", f, ")")

    # Pelvic drop: hip line vs the runner's average level line.
    drop = -pelvis[f]
    pn = Panel(img, box)
    pn.spotlight([HL, HR], 190)
    pn.skeleton(clip, f)
    # The level line drawn towards the right hip: + baseline = left hip lower, so the right side rises.
    level_dir = math.atan2(-math.tan(math.radians(baseline)), 1 if HR[0] > mid[0] else -1)
    half = np.linalg.norm(HR - HL) * 1.3
    back = (mid[0] - math.cos(level_dir) * half, mid[1] - math.sin(level_dir) * half)
    pn.dashed(back, (mid[0] + math.cos(level_dir) * half, mid[1] + math.sin(level_dir) * half))
    pn.segment(HL, HR, COLOR["C"])
    pn.angle(mid, level_dir, ang(mid, HR), COLOR["C"], f"{drop:.1f}°", radius=70, ref_len=1.4)
    pn.tag("Midstance · left foot on the belt")
    save(pn.image(), out, "pelvic-drop")

    # Hip adduction: stance thigh vs vertical.
    add = math.degrees(math.atan2(medial["L"] * (KL[0] - HL[0]), KL[1] - HL[1]))
    pn = Panel(img, box)
    pn.spotlight([HL, KL], 190)
    pn.skeleton(clip, f)
    pn.segment(HL, KL, COLOR["L"])
    pn.angle(HL, math.pi / 2, ang(HL, KL), COLOR["L"], f"{add:+.1f}°", radius=40, ref_len=2.4)
    pn.tag("Midstance · left foot on the belt")
    save(pn.image(), out, "hip-adduction")

    # Hip adduction relative to the pelvis: thigh vs the perpendicular to the hip line.
    # The perpendicular to the hip line that points down the leg.
    perp = ang(HL, HR) - math.pi / 2 if math.sin(ang(HL, HR) - math.pi / 2) > 0 else ang(HL, HR) + math.pi / 2
    rel = math.degrees((ang(HL, KL) - perp + math.pi) % (2 * math.pi) - math.pi) * medial["L"]
    pn = Panel(img, box)
    pn.spotlight([HL, KL, HR], 190)
    pn.skeleton(clip, f)
    pn.segment(HL, HR, COLOR["C"], width=1.4)
    pn.segment(HL, KL, COLOR["L"])
    pn.angle(HL, perp, ang(HL, KL), COLOR["L"], f"{abs(rel):.1f}°", radius=40, ref_len=2.4)
    pn.tag("Midstance · left foot on the belt")
    save(pn.image(), out, "hip-adduction-pelvis")


def raw_vs_filtered(video: Path, keypoints: Path, out: Path):
    """One swing frame where the model's raw foot points and the filtered ones differ visibly."""
    d = json.loads(keypoints.read_text())
    J = d["joints"]
    raw, fil = np.array(d["frames_raw"], dtype=float), np.array(d["frames"], dtype=float)
    feet = [J.index(n) for n in ("ankle_L", "heel_L", "toe_L")]
    diff = np.linalg.norm(raw[:, feet, :2] - fil[:, feet, :2], axis=2).max(1)
    diff[fil[:, feet, 2].min(1) == 0] = 0  # skip frames where points were discarded
    i = int(np.argsort(diff)[-len(diff) // 200])  # a clear but not extreme case
    f = d["start_frame"] + i * d["frame_step"]
    img = read_frames(video, {f})[f]
    pts = [fil[i, k, :2] for k in feet] + [raw[i, k, :2] for k in feet]
    box = box_around(pts, 150, 130, 1.0)
    panels = []
    for data, label in ((raw, "Raw: model output"), (fil, "Filtered: used for the metrics")):
        clip = Clip(video, J, data, d["start_frame"], d["frame_step"], d["events"])
        pn = Panel(img, box, width=PANEL_W // 2)
        pn.skeleton(clip, f, alpha=230, width=1.4)
        for k in feet:
            x, y = pn.xy(data[i, k, :2])
            r = pn.u * 2.6
            pn.draw.ellipse((x - r, y - r, x + r, y + r), fill=COLOR["L"] + (255,), outline=WHITE + (255,), width=int(pn.u * 0.6))
        pn.tag(label)
        panels.append(pn.image())
    print("raw vs filtered (frame", f, f"max foot difference {diff[i]:.0f} px)")
    save(hstack(panels), out, "raw-vs-filtered")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--side-video", type=Path, required=True)
    ap.add_argument("--side-keypoints", type=Path, required=True)
    ap.add_argument("--rear-video", type=Path)
    ap.add_argument("--rear-keypoints", type=Path)
    ap.add_argument("--height-cm", type=float, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, help="JSON file to write {figure: {width, height, version}} to (the web pages read it)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    side_figures(load(args.side_video, args.side_keypoints), args.out, args.height_cm)
    raw_vs_filtered(args.side_video, args.side_keypoints, args.out)
    if args.rear_video and args.rear_keypoints:
        rear_figures(load(args.rear_video, args.rear_keypoints), args.out)
    if args.manifest:
        args.manifest.write_text(json.dumps(dict(sorted(SAVED.items())), indent=2) + "\n")


if __name__ == "__main__":
    main()
