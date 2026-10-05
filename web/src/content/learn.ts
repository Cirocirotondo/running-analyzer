/**
 * Explanations shown in the info popups and on the Learn pages (/learn/<slug>).
 *
 * One entry per Metric and per technical term the interface shows. `short` and `why` feed the popup;
 * `sections` the page. Bodies use a small markup: blank line = new paragraph, lines starting with
 * "- " = bullet list, **bold**, and [text](href) links. Numbers come from docs/typical-ranges.md and
 * api/.../metrics_config.py: keep them in sync when either changes.
 */

import figureSizes from "./learn-figures.json";

export type Group = "side" | "rear" | "concepts";

export interface Topic {
  slug: string;
  title: string;
  group: Group;
  metricKeys?: string[]; // Metric keys (api metrics_config) this topic explains
  short: string; // popup: what it is
  why?: string; // popup: why it matters
  figure?: { name: string; alt: string; caption: string };
  sections: { heading: string; body: string }[];
  sources?: string[];
  related?: string[];
}

export const GROUP_TITLE: Record<Group, string> = {
  side: "Metrics from the side view",
  rear: "Metrics from the rear view",
  concepts: "How to read the results",
};

export const SOURCES: Record<string, { cite: string; url?: string }> = {
  "altman-2012": { cite: "Altman & Davis 2012. A kinematic method for footstrike pattern detection in barefoot and shod runners. Gait Posture 35:298–300.", url: "https://doi.org/10.1016/j.gaitpost.2011.09.104" },
  "bramah-2018": { cite: "Bramah et al. 2018. Is there a pathological gait associated with common soft tissue running injuries? Am J Sports Med 46:3023–3031.", url: "https://doi.org/10.1177/0363546518793657" },
  "ceyssens-2019": { cite: "Ceyssens et al. 2019. Biomechanical risk factors associated with running-related injuries: a systematic review. Sports Med 49:1095–1115.", url: "https://doi.org/10.1007/s40279-019-01110-z" },
  "folland-2017": { cite: "Folland et al. 2017. Running technique is an important component of running economy and performance. Med Sci Sports Exerc 49:1412–1423.", url: "https://doi.org/10.1249/MSS.0000000000001245" },
  "hasegawa-2007": { cite: "Hasegawa et al. 2007. Foot strike patterns of runners at the 15-km point during an elite-level half marathon. J Strength Cond Res 21:888–893.", url: "https://doi.org/10.1519/R-22096.1" },
  "heiderscheit-2011": { cite: "Heiderscheit et al. 2011. Effects of step rate manipulation on joint mechanics during running. Med Sci Sports Exerc 43:296–302.", url: "https://doi.org/10.1249/MSS.0b013e3181ebedf4" },
  "larson-2011": { cite: "Larson et al. 2011. Foot strike patterns of recreational and sub-elite runners in a long-distance road race. J Sports Sci 29:1665–1673.", url: "https://doi.org/10.1080/02640414.2011.610347" },
  "lieberman-2015": { cite: "Lieberman et al. 2015. Effects of stride frequency and foot position at landing on braking force, hip torque, impact peak force and the metabolic cost of running. J Exp Biol 218:3406–3414.", url: "https://doi.org/10.1242/jeb.125500" },
  "malisoux-2023": { cite: "Malisoux et al. 2023. Reference values and determinants of spatiotemporal and kinetic variables in recreational runners. Orthop J Sports Med 11(10).", url: "https://doi.org/10.1177/23259671231204629" },
  "maykut-2015": { cite: "Maykut et al. 2015. Concurrent validity and reliability of 2D kinematic analysis of frontal plane motion during running. Int J Sports Phys Ther 10:136–146.", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC4387721/" },
  "noehren-2013": { cite: "Noehren, Hamill & Davis 2013. Prospective evidence for a hip etiology in patellofemoral pain. Med Sci Sports Exerc 45:1120–1124.", url: "https://doi.org/10.1249/MSS.0b013e31828249d2" },
  "ogueta-2014": { cite: "Ogueta-Alday et al. 2014. Rearfoot striking runners are more economical than midfoot strikers. Med Sci Sports Exerc 46:580–585.", url: "https://doi.org/10.1249/MSS.0000000000000139" },
  "rtmpose-2023": { cite: "Jiang et al. 2023. RTMPose: real-time multi-person pose estimation based on MMPose. arXiv:2303.07399.", url: "https://arxiv.org/abs/2303.07399" },
  "souza-2016": { cite: "Souza 2016. An evidence-based videotaped running biomechanics analysis. Phys Med Rehabil Clin N Am 27:217–236.", url: "https://doi.org/10.1016/j.pmr.2015.08.006" },
  "teng-2014": { cite: "Teng & Powers 2014. Sagittal plane trunk posture influences patellofemoral joint stress during running. J Orthop Sports Phys Ther 44:785–792.", url: "https://doi.org/10.2519/jospt.2014.5249" },
  "van-hooren-2024": { cite: "Van Hooren et al. 2024. The relationship between running biomechanics and running economy: a systematic review and meta-analysis. Sports Med 54:1269–1316.", url: "https://doi.org/10.1007/s40279-024-01997-3" },
  "winter-2009": { cite: "Winter 2009. Biomechanics and Motor Control of Human Movement, 4th ed. Wiley (body segment proportions)." },
  "zeni-2008": { cite: "Zeni, Richards & Higginson 2008. Two simple methods for determining gait events during treadmill and overground walking using kinematic data. Gait Posture 27:710–714.", url: "https://doi.org/10.1016/j.gaitpost.2007.07.007" },
};

const EXAMPLE = "Example from one of our test runs at 14 km/h.";

export const TOPICS: Topic[] = [
  // ------------------------------------------------------------------ side view
  {
    slug: "cadence",
    title: "Cadence",
    group: "side",
    metricKeys: ["cadence"],
    short: "The number of steps you take per minute, counting both feet.",
    why: "It is the technique metric with the clearest evidence: a slightly higher cadence at the same speed reduces the load on knees and hips.",
    figure: { name: "cadence", alt: "Left foot landing, then the right foot landing one step later", caption: `One step: from one foot landing to the other foot landing. ${EXAMPLE}` },
    sections: [
      {
        heading: "What it is",
        body: "Cadence counts every step, left and right: two steps make one stride. On a treadmill at a given speed, cadence and step length are two sides of the same coin. More steps per minute means shorter steps.",
      },
      {
        heading: "How we measure it",
        body: "We find every [initial contact](/learn/gait-cycle), the instant a foot lands, in the [analyzed window](/learn/analyzed-window). Cadence is 60 divided by the time between two consecutive contacts. The value shown is the average over all the steps in the window, and the ± is how much it varies from step to step.\n\nContacts are found from the position of the heel relative to the hip (Zeni 2008), at 120 to 240 frames per second, so each one is timed to within a few milliseconds.",
      },
      {
        heading: "How to read your value",
        body: "Cadence rises with speed, by about 3 steps/min for every km/h, and is a little lower in taller runners. That is why the [typical range](/learn/typical-range) depends on the treadmill speed you entered:\n\n- below 11 km/h: 160–180 steps/min\n- 11 to 13 km/h: 165–185 steps/min\n- 13 to 16 km/h: 168–188 steps/min\n\nThe bands come from 860 recreational runners measured on an instrumented treadmill (Malisoux 2023) and from a group of trained runners (Folland 2017). The often-quoted 180 steps/min comes from elite runners at race pace. It is not a target for everyone.",
      },
      {
        heading: "What the research says",
        body: "In Heiderscheit 2011, runners who raised their cadence by 5–10 % at the same speed took shorter steps, bounced less, landed with the foot closer to the body and absorbed less energy at the knee and hip. Across studies, a higher cadence is also weakly associated with better running economy (Van Hooren 2024).\n\nThese are effects on loads and mechanics. No study has shown that a given cadence prevents injuries.",
      },
      {
        heading: "If you want to change it",
        body: "Change it relative to your own cadence, not towards a fixed number: **+5 % at a time** is enough. A metronome app or music at the target tempo helps. Use it on a few easy runs a week and give it a few weeks to feel natural before going further.",
      },
    ],
    sources: ["malisoux-2023", "folland-2017", "heiderscheit-2011", "van-hooren-2024", "zeni-2008"],
    related: ["step-length", "overstride", "vertical-oscillation"],
  },
  {
    slug: "step-length",
    title: "Step length",
    group: "side",
    metricKeys: ["step_length"],
    short: "How far the belt moves between one foot landing and the other foot landing.",
    why: "It describes how you cover ground at this speed. It is the counterpart of cadence.",
    figure: { name: "cadence", alt: "Left foot landing, then the right foot landing one step later", caption: `A step goes from one foot's contact to the other foot's contact. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "Not from the image. On a treadmill the runner stays in place while the belt moves, so step length = belt speed × time between two contacts. The speed is the one you entered at upload; the contact times come from the video.\n\nTreadmill displays are often a few percent off the real belt speed, and the step length inherits that error.",
      },
      {
        heading: "How to read your value",
        body: "It is **descriptive**: we do not compare it with a typical range, because it depends mostly on speed and on leg length. At the same speed, longer steps mean a lower [cadence](/learn/cadence), and the reverse.",
      },
    ],
    sources: ["heiderscheit-2011"],
    related: ["cadence", "overstride"],
  },
  {
    slug: "contact-time",
    title: "Ground contact time",
    group: "side",
    metricKeys: ["contact_time"],
    short: "How long each foot stays on the belt, from landing to push-off.",
    why: "It describes your running. Research has not linked it to injuries or to running economy.",
    figure: { name: "contact-time", alt: "The same foot at initial contact and at toe-off", caption: `Contact time runs from the foot landing to its toes leaving the belt. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "From the [initial contact](/learn/gait-cycle) of a foot to its toe-off. The landing is found from the heel's position relative to the hip (Zeni 2008). The toe-off is the moment the toe starts rising quickly, which in running is more precise than position-based rules.\n\nAt 120 frames per second one frame is 8 ms; averaged over 25 or more steps the mean is stable within a few milliseconds.",
      },
      {
        heading: "How to read your value",
        body: "Contact time gets shorter as you run faster, by about 17 ms per km/h (Malisoux 2023): roughly 250–320 ms at 10–12 km/h and 230–300 ms at 14 km/h. Heel strikers usually stay on the ground a little longer than midfoot strikers. Left and right within about 5 % of each other is normal.",
      },
      {
        heading: "Why there is no typical range",
        body: "A meta-analysis of 40 studies found no meaningful link between contact time and running economy (Van Hooren 2024), and no prospective study links it to injuries. We show it as a **descriptive** value.",
      },
    ],
    sources: ["malisoux-2023", "van-hooren-2024", "zeni-2008", "hasegawa-2007"],
    related: ["flight-time", "gait-cycle", "foot-strike"],
  },
  {
    slug: "flight-time",
    title: "Flight time",
    group: "side",
    metricKeys: ["flight_time"],
    short: "The time with both feet off the belt, from one foot pushing off to the other foot landing.",
    why: "It describes your running. It has no established link with injuries or running economy.",
    figure: { name: "flight-time", alt: "One foot leaving the belt, then the other foot landing", caption: `Flight runs from one foot's toe-off to the other foot's landing. ${EXAMPLE}` },
    sections: [
      {
        heading: "What it is",
        body: "Running differs from walking because at every step there is a moment with no foot on the ground. Flight time measures it. It is labelled with the foot that pushed off.",
      },
      {
        heading: "How to read your value",
        body: "Usually 80–130 ms at 10–14 km/h; it grows with speed and with longer steps. Direct reference values are scarce, so this range is derived from step time minus contact time.\n\nCareful when comparing with watches or other apps: some call \"flight time\" the whole time one foot is off the ground (the swing, around 450 ms). Ours is the time with **both** feet in the air.",
      },
      {
        heading: "Why there is no typical range",
        body: "Across 18 studies flight time was not associated with running economy (Van Hooren 2024), and there are no injury studies. We show it as a **descriptive** value.",
      },
    ],
    sources: ["van-hooren-2024", "malisoux-2023"],
    related: ["contact-time", "vertical-oscillation"],
  },
  {
    slug: "knee-flexion",
    title: "Knee flexion at initial contact",
    group: "side",
    metricKeys: ["knee_flexion_ic"],
    short: "How bent your knee is at the moment the foot lands. 0° is a straight leg.",
    why: "Landing with an almost straight knee is more common in injured runners and often goes with overstriding.",
    figure: { name: "knee-flexion", alt: "Runner's leg at initial contact with the knee angle highlighted", caption: `The angle between the continuation of the thigh and the shin, at the instant the foot lands. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "In the frame of each [initial contact](/learn/gait-cycle) we take the hip, knee and ankle points and measure how far the shin is bent away from the line of the thigh. The value is the average over all contacts in the window, separately for each leg.\n\nSeen from the side the angle is close to the real one as long as the camera points straight across the treadmill. A camera at an angle makes it look smaller.",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **8–20°**. Healthy runners averaged 10° in Bramah 2018 and 18° in Heiderscheit 2011 (the two labs use different body models), and video studies report 13–16°. The injured runners in Bramah 2018 averaged 6°.",
      },
      {
        heading: "What the research says",
        body: "Bramah 2018 compared 72 runners with common injuries (kneecap pain, IT band syndrome, shin splints, Achilles tendinopathy) with 36 healthy runners. The injured group landed with a straighter knee. The study looked at runners who were already injured, so it cannot say whether the straight knee caused the injury.\n\nRaising cadence tends to bring the foot closer to the body and to increase knee flexion at contact (Heiderscheit 2011).",
      },
      {
        heading: "Limits",
        body: "The link with injuries rests mainly on one study, so we show the range for orientation and do not give advice on this metric.",
      },
    ],
    sources: ["bramah-2018", "heiderscheit-2011"],
    related: ["tibia-angle", "overstride", "cadence"],
  },
  {
    slug: "tibia-angle",
    title: "Tibia angle at initial contact",
    group: "side",
    metricKeys: ["tibia_angle_ic"],
    short: "How much your shin is tilted from vertical when the foot lands. Negative means the foot lands ahead of the knee.",
    why: "A shin sloping forward, with the foot well ahead of the knee, is the clearest visual sign of overstriding.",
    figure: { name: "tibia-angle", alt: "Shin at initial contact with its angle from vertical highlighted", caption: `The shin (knee to ankle) against a vertical line, at the instant the foot lands. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "In each contact frame we take the line from the knee to the ankle and measure its angle from vertical. The sign tells the direction:\n\n- **positive**: the knee is ahead of the ankle\n- **zero**: vertical shin\n- **negative**: the ankle is ahead of the knee, the foot reaches out in front",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **−11° to −2°**. Most runners land with the ankle a little ahead of the knee: video studies report 6 ± 4° (adult women) and 9 ± 3° (adolescents), and trained runners in the lab about 15°. Values more negative than about −12° to −15° suggest overstriding.",
      },
      {
        heading: "What the research says",
        body: "Clinical guidelines describe a near-vertical shin at landing as better at absorbing impact (Souza 2016), and landing with the foot further ahead increases braking at every step (Lieberman 2015). The evidence linking the angle to injuries is indirect, and the reference values come from small groups.",
      },
    ],
    sources: ["souza-2016", "lieberman-2015", "folland-2017"],
    related: ["overstride", "knee-flexion", "cadence"],
  },
  {
    slug: "foot-angle",
    title: "Foot angle at initial contact",
    group: "side",
    metricKeys: ["foot_angle_ic"],
    short: "The angle of your foot to the ground when it lands: positive is toes up (heel first), negative is toes down.",
    why: "It shows which part of the foot touches first, and it decides the foot strike pattern.",
    figure: { name: "foot-angle", alt: "Foot at initial contact with the heel-to-toe line and a horizontal reference", caption: `The heel-to-toe line against the horizontal, at the instant the foot lands. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "In each contact frame we take the heel and toe points and measure the angle of the line between them from horizontal. Those points sit on the outline of the shoe, so the angle includes the shoe's shape: a thick heel or a rocker sole changes it by a few degrees.",
      },
      {
        heading: "How to read your value",
        body: "Heel strikers typically land with 9–17°, a flat foot gives about 0°, and a forefoot landing is below zero. This is a **descriptive** value: no angle has been shown to be better than another. The [foot strike](/learn/foot-strike) page explains the categories.",
      },
      {
        heading: "Limits",
        body: "Foot points are the least precise part of the skeleton: the foot is small, moves fast and is often blurred or hidden. We average every contact in the window to reduce the error.",
      },
    ],
    sources: ["altman-2012", "folland-2017"],
    related: ["foot-strike", "tibia-angle"],
  },
  {
    slug: "foot-strike",
    title: "Foot strike pattern",
    group: "side",
    metricKeys: ["foot_strike_pattern"],
    short: "Which part of the foot lands first: the heel (rearfoot), the whole foot (midfoot) or the ball of the foot (forefoot).",
    why: "It is descriptive: no pattern has been shown to be better for injuries or for economy.",
    figure: { name: "foot-angle", alt: "Foot at initial contact with the heel-to-toe line", caption: `The pattern comes from the foot angle at landing. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we classify it",
        body: "From your average [foot angle at initial contact](/learn/foot-angle), with the thresholds of Altman & Davis 2012:\n\n- **rearfoot**: above 8°\n- **midfoot**: from −1.6° to 8°\n- **forefoot**: below −1.6°",
      },
      {
        heading: "How common each pattern is",
        body: "Most runners land on the heel: 89 % of recreational runners in a road race (Larson 2011) and 75 % of elite half-marathoners (Hasegawa 2007), where the fastest included more midfoot strikers.",
      },
      {
        heading: "What the research says",
        body: "No pattern has been shown to reduce injuries. In one study heel strikers were even slightly more economical at 11–13 km/h (Ogueta-Alday 2014). Switching pattern abruptly moves load from the knee to the calf and Achilles tendon, so it is not a goal in itself.",
      },
      {
        heading: "Limits",
        body: "Video separates heel strikers from the others reliably. Midfoot versus forefoot is less certain.",
      },
    ],
    sources: ["altman-2012", "larson-2011", "hasegawa-2007", "ogueta-2014"],
    related: ["foot-angle", "contact-time"],
  },
  {
    slug: "overstride",
    title: "Ankle ahead of hip at initial contact",
    group: "side",
    metricKeys: ["overstride"],
    short: "How far in front of your hips the ankle is when the foot lands.",
    why: "Landing far ahead of the body brakes you at every step. It usually comes with a low cadence.",
    figure: { name: "overstride", alt: "Horizontal distance between the hips and the landing ankle", caption: `The horizontal distance between the middle of the hips and the ankle of the landing foot. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "In each contact frame we measure the horizontal distance between the midpoint of the two hips and the ankle of the landing foot. To turn pixels into centimetres we use your height: thigh plus shin is about 49 % of body height (Winter 2009), and we measure that length in the video.\n\nIf the camera is not straight across the treadmill or not at hip height, the value can be off by a few centimetres.",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **5–15 cm**. The reference comes from Heiderscheit 2011, where the heel landed 9 ± 4 cm ahead of the body's centre of mass. We use the ankle and the hips, slightly different landmarks, so compare loosely.",
      },
      {
        heading: "What the research says",
        body: "When runners raised their cadence by 10 %, this distance fell from 9 to 7 cm together with braking (Heiderscheit 2011). Landing further ahead increases the braking force (Lieberman 2015). No study gives an injury threshold.",
      },
      {
        heading: "If you want to change it",
        body: "Do not try to place the foot further back on purpose. A slightly higher [cadence](/learn/cadence) usually brings the foot closer to the body by itself.",
      },
    ],
    sources: ["heiderscheit-2011", "lieberman-2015", "winter-2009"],
    related: ["tibia-angle", "cadence", "knee-flexion"],
  },
  {
    slug: "trunk-lean",
    title: "Trunk forward lean at midstance",
    group: "side",
    metricKeys: ["trunk_lean_midstance"],
    short: "How much your trunk leans forward from vertical while the foot is under the body.",
    why: "A moderate forward lean is normal. It shifts load between the knee and the hip.",
    figure: { name: "trunk-lean", alt: "Line from hips to shoulders with its angle from vertical", caption: `The line from the middle of the hips to the middle of the shoulders, against a vertical line, at midstance. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "At [midstance](/learn/gait-cycle), halfway between landing and toe-off, we take the line from the midpoint of the hips to the midpoint of the shoulders and measure its angle from vertical. Positive is leaning forward.",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **4–12°**. Two laboratory studies found 7.3 ± 3.6° (Teng & Powers 2014) and 7.8 ± 4.5° (Folland 2017).",
      },
      {
        heading: "What the research says",
        body: "The findings point in different directions. Leaning more reduced the stress on the kneecap in a modelling study (Teng & Powers 2014), while injured runners leaned more in Bramah 2018. Neither shows that one value is better, so the range is for orientation only.",
      },
      {
        heading: "Limits",
        body: "A straight line from hips to shoulders does not see how the back is curved, and arm swing moves the shoulder points a little.",
      },
    ],
    sources: ["teng-2014", "folland-2017", "bramah-2018"],
    related: ["gait-cycle", "joint-angles"],
  },
  {
    slug: "vertical-oscillation",
    title: "Vertical oscillation of the head",
    group: "side",
    metricKeys: ["vertical_oscillation"],
    short: "How much your body moves up and down during each step, measured at the head.",
    why: "Bouncing more than needed costs energy: lower oscillation is moderately linked with better running economy.",
    figure: { name: "vertical-oscillation", alt: "Head at its highest and lowest point in one stride", caption: `The body is lowest at midstance and highest in flight. ${EXAMPLE}` },
    sections: [
      {
        heading: "How we measure it",
        body: "We follow the vertical position of the head. For each stride we take the highest point minus the lowest, convert pixels to centimetres using your height, and average all strides.\n\nWhy the head and not the hips: the trunk moves as one piece, but the hip points the pose model finds slide up and down with the thighs. In our tests with tape markers the hips seemed to move 15–18 cm per step while the head and shoulders moved 8–10 cm, so the hips would double the value.",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **6–10 cm**. Malisoux 2023 found 7.7 ± 1.2 cm in 860 recreational runners and Heiderscheit 2011 8.7 ± 1.3 cm.\n\nThose studies measure the body's centre of mass. The head bobs a little more than the centre of mass, so a value just above the range is not a concern by itself.",
      },
      {
        heading: "What the research says",
        body: "Across 23 studies, more vertical oscillation went with a higher energy cost (Van Hooren 2024, moderate association). In Folland 2017 it was the single technique variable that best predicted running economy. Raising cadence by 10 % reduced it from 8.7 to 7.3 cm (Heiderscheit 2011).",
      },
      {
        heading: "If you want to change it",
        body: "A slightly higher [cadence](/learn/cadence) is the most reliable way. Thinking of running \"quietly\", pushing forward rather than up, also helps some runners.",
      },
    ],
    sources: ["malisoux-2023", "heiderscheit-2011", "folland-2017", "van-hooren-2024"],
    related: ["cadence", "flight-time"],
  },
  // ------------------------------------------------------------------ rear view
  {
    slug: "pelvic-drop",
    title: "Contralateral pelvic drop (under validation)",
    group: "rear",
    metricKeys: ["pelvic_drop"],
    short: "How much the hip of the swinging leg drops while the other foot is on the ground, seen from behind.",
    why: "Research links it to common running injuries, but our video measurement of it is not reliable yet: we show it as descriptive and give no advice on it.",
    figure: { name: "pelvic-drop", alt: "Seen from behind, the line between the hips tilts down towards the side of the swinging leg", caption: "With the left foot on the belt, the right side of the pelvis drops. This is the step with the clearest drop in a test run; the dashed line is the runner's average level." },
    sections: [
      {
        heading: "What it is",
        body: "When one foot is on the ground, the hip muscles of that leg, mainly the gluteus medius, keep the pelvis level. If they do not hold it, the opposite side drops: \"contralateral\" means the side opposite the leg on the ground. The value is labelled with the leg on the ground: \"left\" is measured while the left foot is on the belt.",
      },
      {
        heading: "How we measure it",
        body: "From the rear video we take the line between the two hip points and measure its tilt against your own average level over the whole clip. That cancels a slightly tilted camera and any habitual tilt in your posture. We take the peak during each stance and average all of them.",
      },
      {
        heading: "Why it is under validation",
        body: "The hip points come from the pose model, which estimates where the hip joints are inside the body. In our tests those points follow the thighs: the hip of the swinging leg is pulled up with it, which tilts the line between the hips by 2–3°, as much as the drop we want to measure, and in the opposite direction. Until we confirm the measurement against markers on the pelvis, the value is shown without a typical range and without advice.",
      },
      {
        heading: "How to read your value",
        body: "Typical range: **2–7°**. Healthy runners averaged 3.7 ± 1.9° in a 3D lab study (Bramah 2018) and 4–6° in video studies; injured runners 6.4–7.8°. Video slightly underestimates the 3D value (Maykut 2015).",
      },
      {
        heading: "What the research says",
        body: "In Bramah 2018 every extra degree of drop came with 80 % higher odds of being in the injured group, and the pattern was the same for kneecap pain, IT band syndrome, shin splints and Achilles tendinopathy. The study compared runners who were already injured, so it shows an association, not a cause.",
      },
      {
        heading: "Limits",
        body: "Besides the issue above, the rear camera must be centred and at hip height, and the hips are small in the image: one pixel of error is about half a degree to one degree. If pelvic control worries you, a physiotherapist can assess it in person.",
      },
    ],
    sources: ["bramah-2018", "maykut-2015", "heiderscheit-2011", "ceyssens-2019"],
    related: ["hip-adduction", "hip-adduction-pelvis", "advice"],
  },
  {
    slug: "hip-adduction",
    title: "Hip adduction at midstance",
    group: "rear",
    metricKeys: ["hip_adduction"],
    short: "How much your thigh angles inwards, towards the other leg, while the foot is on the ground, seen from behind.",
    why: "Higher values were found in runners who later developed knee pain or IT band syndrome, mainly in women.",
    figure: { name: "hip-adduction", alt: "Seen from behind, the thigh of the stance leg against a vertical line", caption: "The thigh of the leg on the belt (hip to knee) against a vertical line. Example from a test run." },
    sections: [
      {
        heading: "How we measure it",
        body: "In the rear video we take the line from the hip to the knee of the leg on the ground and measure its angle from vertical. Positive means the knee is closer to the midline than the hip. We take the peak during each stance and average all of them.",
      },
      {
        heading: "How to read your value",
        body: "Typical range from video: **6–13°**; 3D lab measures give 8–14°, because video underestimates this angle by 2–3° (Maykut 2015). Healthy runners averaged 9.7° and injured runners 13.0° in Bramah 2018.",
      },
      {
        heading: "What the research says",
        body: "Two studies followed healthy women over time: those who developed kneecap pain or IT band syndrome had shown more hip adduction before the injury (Noehren 2013). A systematic review rates this as limited evidence, found in women and not in mixed groups (Ceyssens 2019). Raising cadence by 10 % lowered it by about 2° (Heiderscheit 2011).",
      },
      {
        heading: "Limits",
        body: "The hip point is the model's estimate of the joint centre inside the body, so the absolute value depends on the model. Compare your own sessions with each other rather than reading single degrees.",
      },
    ],
    sources: ["bramah-2018", "noehren-2013", "ceyssens-2019", "maykut-2015", "heiderscheit-2011"],
    related: ["pelvic-drop", "hip-adduction-pelvis"],
  },
  {
    slug: "hip-adduction-pelvis",
    title: "Hip adduction relative to the pelvis",
    group: "rear",
    metricKeys: ["hip_adduction_rel_pelvis"],
    short: "The thigh's inward angle measured from the pelvis rather than from vertical.",
    why: "It separates the thigh moving inwards from the pelvis tilting. It is descriptive.",
    figure: { name: "hip-adduction-pelvis", alt: "Thigh of the stance leg against a line perpendicular to the hips", caption: "The thigh of the leg on the belt against the perpendicular to the line between the hips. Example from a test run." },
    sections: [
      {
        heading: "What it adds",
        body: "Hip adduction can grow in two ways: the knee moves inwards, or the pelvis drops on the other side and carries the thigh with it. Measured against the pelvis, the second part counts too. It is roughly [hip adduction](/learn/hip-adduction) plus [pelvic drop](/learn/pelvic-drop).",
      },
      {
        heading: "How to read your value",
        body: "It is **descriptive**: there are no reference values measured this way on video. Use it together with the other two rear-view metrics.",
      },
    ],
    sources: ["maykut-2015"],
    related: ["hip-adduction", "pelvic-drop"],
  },
  // ------------------------------------------------------------------ concepts
  {
    slug: "gait-cycle",
    title: "Phases of the running stride",
    group: "concepts",
    short: "A stride goes from one foot landing to the same foot landing again: initial contact, midstance, toe-off and swing.",
    why: "Each metric is measured at a precise moment of the stride.",
    figure: { name: "gait-cycle", alt: "Four frames: initial contact, midstance, toe-off and swing", caption: `The four moments the metrics refer to, for the left leg. ${EXAMPLE}` },
    sections: [
      {
        heading: "The four moments",
        body: "- **Initial contact**: the foot touches the belt. Knee, shin and foot angles and the ankle-ahead-of-hip distance are measured here.\n- **Midstance**: halfway through the contact, the foot is under the body. Trunk lean, pelvic drop and hip adduction are measured here.\n- **Toe-off**: the toes leave the belt. Contact time ends here.\n- **Swing**: the leg travels forward in the air. For a moment both feet are off the belt: that is the flight time.",
      },
      {
        heading: "How we find them",
        body: "Initial contact is the instant the heel is furthest ahead of the hip (Zeni 2008). Toe-off is the moment the toe starts rising quickly. From behind, a foot is on the belt while the ankle stays on the lowest part of its path.",
      },
      {
        heading: "Left and right",
        body: "Values marked left or right belong to that foot's contacts. From the side we report only the leg nearer the camera: in our tests the far leg, often hidden by the near one or by the treadmill, came out with a knee flexion of 7–10° instead of 17°. To measure the other leg, record a session from the other side.",
      },
    ],
    sources: ["zeni-2008"],
    related: ["contact-time", "flight-time", "joint-angles"],
  },
  {
    slug: "typical-range",
    title: "Typical range",
    group: "concepts",
    short: "The range of values where most healthy recreational runners fall, taken from published studies.",
    why: "It gives orientation. It is not a pass-or-fail threshold.",
    sections: [
      {
        heading: "Where the numbers come from",
        body: "Each range comes from studies that measured groups of runners, mostly in laboratories, at speeds similar to yours. The source is linked under every metric. When a value depends on speed, as cadence does, we use the band for the treadmill speed you entered.",
      },
      {
        heading: "How to read it",
        body: "- A range describes a group. Being outside it does not mean something is wrong with you, and being inside does not guarantee anything.\n- The bar on each metric card shows the typical range in green, with the same width again on each side. The marker is your value.\n- Laboratory studies mostly use 3D motion capture, while we use 2D video. For some angles the two differ by a few degrees; each metric's page says how much.\n- Only two metrics, cadence and vertical oscillation, are both well supported by research and reliably measured, so only they [give advice](/learn/advice) when you are outside the range.",
      },
      {
        heading: "During the beta",
        body: "The ranges are checked against the original studies before the app leaves the beta, and may change.",
      },
    ],
    related: ["metric-states", "advice", "confidence"],
  },
  {
    slug: "metric-states",
    title: "Measured, descriptive, not measurable",
    group: "concepts",
    short: "The label on each metric card: compared with a typical range, shown only as a description, not reliable because of how it was filmed, or not measured in this video.",
    sections: [
      {
        heading: "Measured",
        body: "The metric was measured reliably and is compared with its [typical range](/learn/typical-range).",
      },
      {
        heading: "Descriptive",
        body: "The value describes how you run, but we do not compare it with a range. Either research has not linked it to injuries or economy (contact time, flight time, foot strike), or it depends mostly on other things, such as speed or shoes (step length, foot angle).",
      },
      {
        heading: "Not reliable (!)",
        body: "The metric has a value, but a problem found in the recording may bias it, so we mark it with \"! not reliable\" and give no advice on it. The usual cause is a camera below hip height: in our tests, filming from the floor changed knee flexion by about 5° and the foot angle by 4–9°. A tilted phone or a runner small in the frame have the same effect on other metrics. The upload page tells you right after each upload, so you can film again before analyzing.",
      },
      {
        heading: "Not measurable",
        body: "We could not measure it reliably in this video. The card says why:\n\n- **fewer than 6 gait cycles**: not enough steps to average. Record at least 20 seconds of steady running.\n- **keypoints not tracked reliably**: the body points had low [confidence](/learn/confidence). Usually the legs were hidden, blurred or out of frame.\n\nWe prefer showing nothing to showing a number we do not trust.",
      },
    ],
    related: ["confidence", "typical-range"],
  },
  {
    slug: "confidence",
    title: "Cycles and confidence",
    group: "concepts",
    short: "Under each metric: how many steps were averaged, and how sure the pose model was about the body points it used.",
    sections: [
      {
        heading: "Cycles and ±",
        body: "Each metric is measured on every step or stride in the [analyzed window](/learn/analyzed-window) and then averaged. \"Cycles\" is how many were used. The ± after the value is the standard deviation: how much the value varied from step to step. A small ± means a consistent technique and a consistent measurement.",
      },
      {
        heading: "Confidence",
        body: "The pose model gives every body point a score between 0 and 100 %: how sure it is that the point is where it says. The confidence shown is the average score of the points that metric uses. Below 50 % the metric is shown as [not measurable](/learn/metric-states).",
      },
      {
        heading: "What lowers it",
        body: "Legs hidden by the treadmill frame or by the other leg, motion blur in low light, baggy clothes, the body partly out of frame, and a camera placed very low or at an angle.",
      },
    ],
    related: ["skeleton", "metric-states"],
  },
  {
    slug: "advice",
    title: "Advice",
    group: "concepts",
    short: "Suggestions given only when a metric with solid evidence is outside its typical range.",
    why: "It is a starting point for your training, not a diagnosis.",
    sections: [
      {
        heading: "When we give advice",
        body: "Only for metrics where research shows at least a moderate link with load, injuries or economy, and that we measure reliably from video, and only when your value is outside the [typical range](/learn/typical-range):\n\n- [cadence](/learn/cadence) below the range\n- [vertical oscillation](/learn/vertical-oscillation) above the range\n\n[Pelvic drop](/learn/pelvic-drop) would qualify on evidence, but our measurement of it is still under validation. For the other metrics the evidence is too weak to recommend a change.",
      },
      {
        heading: "How to use it",
        body: "Change one thing at a time, gradually, over a few weeks, and record a new session to see the effect. If you have pain, see a physiotherapist or a sports doctor: this app does not diagnose.",
      },
    ],
    related: ["typical-range", "cadence", "pelvic-drop"],
  },
  {
    slug: "analyzed-window",
    title: "Analyzed window",
    group: "concepts",
    short: "The 20 seconds of steady running that the metrics come from. The player only plays this part.",
    sections: [
      {
        heading: "Why only part of the video",
        body: "The start of a recording usually shows the treadmill speeding up or the runner settling in, and the end the runner slowing down. First we scan the whole video quickly, at about 30 frames per second, and pick the 20 seconds where the step timing is most regular and the runner stays in frame. Then we analyse that window at full frame rate.",
      },
      {
        heading: "Why 20 seconds",
        body: "At running cadences that is more than 25 steps per leg: enough for stable averages. A longer window would add little precision and much more processing time.",
      },
      {
        heading: "Rear view",
        body: "The rear video is analysed from the start of steady running to its end. Getting on or off the belt is cut out automatically.",
      },
    ],
    related: ["slow-motion", "confidence"],
  },
  {
    slug: "slow-motion",
    title: "Slow-motion videos",
    group: "concepts",
    short: "Slow-motion clips are recorded at 120 or 240 frames per second and played back slower. All the times we show are real times.",
    sections: [
      {
        heading: "How phones store slow motion",
        body: "A phone recording slow motion captures 120 or 240 frames per second but saves the file to play at 30 frames per second, so one real second lasts 4 or 8 seconds on screen. The file also notes the real capture rate. We read it and convert every time back to real time: contact times, flight times and cadence are all in real time.",
      },
      {
        heading: "Why it helps",
        body: "At 240 frames per second each frame is about 4 milliseconds apart, so landing and toe-off are timed much more precisely than at 30 or 60. We analyse at up to 120 frames per second, which loses less than 1 % of precision compared with 240.",
      },
      {
        heading: "If the slow motion is not recognised",
        body: "Some gallery apps drop the capture rate when they export a clip. If the analysis looks implausibly slow, upload the original file from the phone.",
      },
    ],
    related: ["analyzed-window"],
  },
  {
    slug: "skeleton",
    title: "The skeleton on the video",
    group: "concepts",
    short: "The body points our pose model found in each frame, joined into a stick figure. Every metric is computed from these points.",
    figure: { name: "raw-vs-filtered", alt: "The same frame with the model's raw points and with the filtered points", caption: "Raw and filtered points on the same frame. In fast swing the filter can trail the foot by a few centimetres; at landing, where the metrics are measured, the foot moves slowly and the two agree." },
    sections: [
      {
        heading: "Where the points come from",
        body: "A pose estimation model (RTMPose) looks at every frame and finds 26 points of the body. We use 13: shoulders, hips, knees, ankles, heels, toes and nose. Yellow is the left side, blue the right side.",
      },
      {
        heading: "Filtered and raw",
        body: "- **Raw** is exactly what the model found in each frame. It shakes by a few pixels from one frame to the next.\n- **Filtered** is what the metrics use: the trajectories are smoothed to remove that shaking while keeping the running movement. Points the model was unsure about are removed and filled in from the frames before and after.",
      },
      {
        heading: "Red points",
        body: "A red point was discarded: either the model's confidence was low, or the point made a limb implausibly long or short, like a shin that suddenly grows by a third. Its position was filled in from neighbouring frames.",
      },
      {
        heading: "Why it is sometimes wrong",
        body: "When a leg passes behind the treadmill frame or the other leg, the model has to guess, and it can be off by several centimetres for a few frames. The same happens with motion blur in low light and with a camera placed on the floor. Metrics average 25 or more steps, so a few wrong frames shift them very little. A camera at hip height, with nothing between it and the runner, gives the best skeleton.",
      },
      {
        heading: "Near leg and far leg",
        body: "From the side, the leg nearer the camera is seen best, and the metrics use only that leg. The angles on the video are shown on the near leg by default; \"both\" also draws the far leg, whose angles are only approximate.",
      },
    ],
    sources: ["rtmpose-2023"],
    related: ["joint-angles", "confidence"],
  },
  {
    slug: "joint-angles",
    title: "Angles on the video",
    group: "concepts",
    short: "The joint angles drawn on the player, frame by frame. On a landing frame they match the values on the metric cards.",
    figure: { name: "thigh-angle", alt: "Thigh angle at initial contact and at toe-off", caption: `The hip angle at landing (thigh ahead of the body) and at toe-off (thigh behind). ${EXAMPLE}` },
    sections: [
      {
        heading: "Side view",
        body: "- **Knee**: knee flexion, 0° is a straight leg. See [knee flexion](/learn/knee-flexion).\n- **Hip**: the thigh against vertical. Positive means the knee is ahead of the hip, as at landing; negative means behind, as at toe-off.\n- **Tibia**: the shin against vertical. Positive means the knee is ahead of the ankle. See [tibia angle](/learn/tibia-angle).\n- **Foot**: the heel-to-toe line against horizontal. Positive means toes up. See [foot angle](/learn/foot-angle).\n- **Trunk**: the hips-to-shoulders line against vertical. Positive means leaning forward. See [trunk lean](/learn/trunk-lean).",
      },
      {
        heading: "Rear view",
        body: "- **Pelvis**: the tilt of the line between the hips against your average level, and which side is lower. See [pelvic drop](/learn/pelvic-drop).\n- **Hip adduction**: each thigh against vertical. Positive means the knee is towards the midline. See [hip adduction](/learn/hip-adduction).\n- **Tibia**: each shin against vertical. Positive means the knee is nearer the midline than the ankle; negative means the foot lands under or across the midline, a narrow \"crossover\" landing. It is shown on the video only: there are no reliable reference values from video for it.\n\nWe do not show a rearfoot (heel) angle. From behind, video cannot place the heel bone precisely, and studies found it among the least reliable video measures.",
      },
      {
        heading: "A tilted phone",
        body: "Angles against the vertical or the horizontal (hip, tibia, foot, trunk, hip adduction) shift one-to-one with a tilted phone. We measure the tilt from the edge of the treadmill and correct both the metrics and the angles on the video, so a phone rotated by a couple of degrees no longer matters.",
      },
      {
        heading: "Why the numbers change at every frame",
        body: "The angles follow the movement continuously. The metrics take them at one precise moment of the stride, landing or midstance, and average many strides. Step through frames with the frame buttons to see a value at a landing.",
      },
    ],
    related: ["skeleton", "gait-cycle"],
  },
  {
    slug: "your-data",
    title: "Why we ask for your data",
    group: "concepts",
    short: "Height, sex and treadmill speed are needed to turn the video into centimetres and to pick the right reference values.",
    sections: [
      {
        heading: "Height",
        body: "A video measures pixels, not centimetres. Thigh plus shin is about 49 % of body height (Winter 2009), so measuring your leg in the video tells us how many centimetres a pixel is. Distances such as the ankle ahead of the hip and the vertical oscillation depend on it.",
      },
      {
        heading: "Treadmill speed",
        body: "Cadence, contact time and step length change with speed, so the [typical range](/learn/typical-range) is chosen for your speed. Step length is computed from speed and step time.",
      },
      {
        heading: "Sex",
        body: "Some reference values differ between men and women. When a study gives separate values, we use the ones that match.",
      },
      {
        heading: "Weight, birth year and incline",
        body: "They are not used for the metrics yet. Studies show that weight and age affect contact time and cadence, and we plan to use them for more specific ranges. Reference values come from flat running, so keep the incline at 0–1 % if you want to compare sessions.",
      },
    ],
    sources: ["winter-2009", "malisoux-2023"],
    related: ["typical-range"],
  },
];

export const TOPIC_BY_SLUG: Record<string, Topic> = Object.fromEntries(TOPICS.map((t) => [t.slug, t]));

export const TOPIC_BY_METRIC: Record<string, Topic> = Object.fromEntries(TOPICS.flatMap((t) => (t.metricKeys ?? []).map((k) => [k, t])));

export interface Figure {
  src: string;
  width: number;
  height: number;
}

/** The rendered figure's URL (versioned by content) and size, from the manifest prototype/learn_figures.py writes. */
export function figureFile(name: string): Figure | null {
  const f = (figureSizes as Record<string, { width: number; height: number; version: string }>)[name];
  return f ? { src: `/figures/learn/${name}.jpg?v=${f.version}`, width: f.width, height: f.height } : null;
}
