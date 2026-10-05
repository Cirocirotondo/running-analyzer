"""Metric definitions: labels, units, which are descriptors, which may produce Advice,
and Typical Ranges with their source. Values and confidence from docs/typical-ranges.md;
every range must be re-checked against the original study before leaving the beta.

A range applies when the Session speed is inside [speed_min, speed_max) km/h and the
Runner's sex matches (None = any). Outside every band the Metric has no Typical Range.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Range:
    low: float
    high: float
    source: str
    speed_min: float = 0.0
    speed_max: float = 99.0
    sex: str | None = None


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    unit: str | None
    view: str
    descriptor: bool = False
    advice_eligible: bool = False
    ranges: tuple[Range, ...] = field(default_factory=tuple)
    higher_is: str | None = None  # "worse" | "better" | None, drives the Advice wording

    def range_for(self, speed_kmh: float, sex: str | None) -> Range | None:
        for r in self.ranges:
            if r.speed_min <= speed_kmh < r.speed_max and (r.sex is None or r.sex == sex):
                return r
        return None


METRICS: dict[str, Metric] = {
    m.key: m
    for m in [
        Metric(
            "cadence", "Cadence", "steps/min", "side", advice_eligible=True, higher_is="better",
            ranges=(
                Range(160, 180, "malisoux-2023", 8, 11),
                Range(165, 185, "malisoux-2023", 11, 13),
                Range(168, 188, "malisoux-2023", 13, 16),
            ),
        ),
        Metric("step_length", "Step length (from speed and cadence)", "cm", "side", descriptor=True),
        Metric("contact_time", "Ground contact time", "ms", "side", descriptor=True),
        Metric("flight_time", "Flight time", "ms", "side", descriptor=True),
        Metric("knee_flexion_ic", "Knee flexion at initial contact", "deg", "side", ranges=(Range(8, 20, "bramah-2018"),)),
        Metric("tibia_angle_ic", "Tibia angle at initial contact", "deg", "side", ranges=(Range(-11, -2, "souza-2016"),)),
        Metric("foot_angle_ic", "Foot angle at initial contact", "deg", "side", descriptor=True),
        Metric("foot_strike_pattern", "Foot strike pattern", None, "side", descriptor=True),
        Metric("overstride", "Ankle ahead of hip at initial contact", "cm", "side", ranges=(Range(5, 15, "heiderscheit-2011"),)),
        Metric("trunk_lean_midstance", "Trunk forward lean at midstance", "deg", "side", ranges=(Range(4, 12, "teng-2014"),)),
        Metric(
            "vertical_oscillation", "Vertical oscillation of the head", "cm", "side", advice_eligible=True, higher_is="worse",
            ranges=(Range(6, 10, "malisoux-2023"),),
        ),
        # Descriptive until validated: the pose model's hip points follow the thighs, which tilts the
        # hip line by as much as the drop itself (10-04 validation). No range, no Advice.
        Metric("pelvic_drop", "Contralateral pelvic drop (under validation)", "deg", "rear", descriptor=True),
        Metric("hip_adduction", "Hip adduction at midstance", "deg", "rear", ranges=(Range(6, 13, "bramah-2018"),)),
        Metric("hip_adduction_rel_pelvis", "Hip adduction relative to the pelvis", "deg", "rear", descriptor=True),
    ]
}

# Whole-body Metrics: with both Side Views they are the mean of the two (each View contributes its Near
# Leg's strides); all other side Metrics belong to one leg and come from that leg's View only.
WHOLE_BODY = {"cadence", "step_length", "vertical_oscillation", "trunk_lean_midstance"}

# Recording Check warnings and the Metrics they make Unreliable (10-04 camera validation: a camera
# below hip height moved knee flexion by ~5°, tibia by 2–3°, foot angle by 4–9°; a tilted phone moves
# every angle against the vertical; a small runner leaves few pixels per segment).
UNRELIABLE_WHEN: dict[str, set[str]] = {
    "camera_low": {"knee_flexion_ic", "tibia_angle_ic", "foot_angle_ic", "foot_strike_pattern"},
    "camera_high": {"knee_flexion_ic", "tibia_angle_ic", "foot_angle_ic", "foot_strike_pattern"},
    "tilted": {"tibia_angle_ic", "foot_angle_ic", "foot_strike_pattern", "trunk_lean_midstance", "hip_adduction", "hip_adduction_rel_pelvis"},
    "runner_small": {"knee_flexion_ic", "tibia_angle_ic", "foot_angle_ic", "foot_strike_pattern", "trunk_lean_midstance",
                     "overstride", "vertical_oscillation", "pelvic_drop", "hip_adduction", "hip_adduction_rel_pelvis"},
}


def foot_strike(foot_angle_deg: float) -> str:
    """Altman & Davis 2012 thresholds on the foot angle at initial contact."""
    return "rearfoot" if foot_angle_deg > 8.0 else "forefoot" if foot_angle_deg < -1.6 else "midfoot"


SOURCES: dict[str, dict] = {
    "malisoux-2023": {"title": "Malisoux et al. 2023, Orthop J Sports Med", "url": "https://doi.org/10.1177/23259671231204629"},
    "bramah-2018": {"title": "Bramah et al. 2018, Am J Sports Med", "url": "https://doi.org/10.1177/0363546518793657"},
    "heiderscheit-2011": {"title": "Heiderscheit et al. 2011, Med Sci Sports Exerc", "url": "https://doi.org/10.1249/MSS.0b013e3181ebedf4"},
    "souza-2016": {"title": "Souza 2016, Phys Med Rehabil Clin N Am", "url": "https://doi.org/10.1016/j.pmr.2015.08.006"},
    "teng-2014": {"title": "Teng & Powers 2014, J Orthop Sports Phys Ther", "url": "https://doi.org/10.2519/jospt.2014.5249"},
}

ADVICE_TEXT = {
    "cadence_low": "Your cadence ({mean:.0f} steps/min) is below the typical range for this speed ({low:.0f}–{high:.0f}). Increasing it by 5–10 % reduces loads on the hip and knee (Heiderscheit 2011). Try short intervals at a slightly higher turnover and let it settle.",
    "vertical_oscillation_high": "Your vertical oscillation ({mean:.1f} cm) is above the typical range ({low:.0f}–{high:.0f} cm). A slightly higher cadence usually reduces it; lower oscillation is weakly associated with better running economy.",
}
