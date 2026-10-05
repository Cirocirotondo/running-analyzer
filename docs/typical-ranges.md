# Typical ranges for 2D running-technique metrics (treadmill, 10–14 km/h)

Reference values collected from peer-reviewed sources for the metrics the app reports from
2D video. Every number is quoted as stated in the source, with where it was read
(abstract / table / text). Where a number was only available from an abstract or from a
search-engine excerpt of a paywalled full text, that is stated explicitly. "not found" means
the value could not be retrieved, not that it does not exist.

Research date: 2026-10-03. Abbreviations: IC = initial contact, CPD = contralateral pelvic
drop, RFS/MFS/FFS = rear-/mid-/forefoot strike, RE = running economy, VO = vertical
oscillation, GCT = ground contact time, PFP = patellofemoral pain, ITBS = iliotibial band
syndrome, MTSS = medial tibial stress syndrome, AT = Achilles tendinopathy.

---

## General caveats (read first)

- **Weak and inconsistent injury links.** Ceyssens 2019 (systematic review of 16 prospective
  studies, 13 high quality): "a large number of biomechanical variables were evaluated,
  producing inconsistent evidence overall"; only "limited evidence indicated greater peak hip
  adduction in female runners developing patellofemoral pain and iliotibial band syndrome"
  (abstract). Vertical loading rate findings were inconsistent.
- **Small share of economy explained.** Van Hooren 2024 (51 studies, 1,115 participants):
  "Running biomechanics can explain 4–12% of the between-individual variation in RE when
  considered in isolation" (abstract). Associations were not always consistent across speeds.
- **Group averages are not individual cut-offs.** All "typical ranges" below are means ± SD of
  groups, mostly measured with 3D motion capture in laboratories. They describe where most
  healthy runners fall; they are not validated diagnostic thresholds for an individual.
- **2D ≠ 3D.** Maykut 2015 (n = 24, treadmill): 2D hip adduction 11.2 ± 2.7° vs 3D 14.0 ± 3.7°
  (right), r = 0.62; CPD 2D 4.6 ± 2.1° vs 3D 5.2 ± 1.4°; knee abduction poorly related
  (r = 0.16 right) (Table 3). Dingenen 2018 (n = 21, test-retest one week apart): 2D is reliable
  across days; lateral trunk, femoral adduction and foot inclination ICC 0.90–0.99; a mean of
  at least ~7 steps is needed (abstract). Pipkin 2016 (n = 15, 120 fps, categorical scoring):
  intra-rater agreement substantial-to-excellent for 11/15 variables but inter-rater only for
  5/15 (abstract). A 2023 IJSPT categorical study (n = 33, 60 fps phone video): overstriding and
  knee window most reliable (κ 0.78–0.92), pelvic drop and heel eversion least (κ 0.05–0.60).
- **Speed and sex matter.** Cadence, GCT, VO and foot strike all change with speed
  (Malisoux 2023, Hasegawa 2007), and several norms were built on single-sex samples.
- **Treadmill vs overground.** Most laboratory norms are treadmill at a fixed speed; race
  observations (Larson, Hasegawa) are overground.

---

## 1. Cadence (steps/min)

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Heiderscheit 2011 | 45 healthy recreational runners, age 32.7 ± 15.5, ≥24 km/wk, sex not reported | self-selected 2.9 ± 0.5 m/s (≈10.4 km/h) | 3D, instrumented treadmill | preferred step rate 172.6 ± 8.8 steps/min | Methods text | +5 % / +10 % step rate reduced step length (100.8→96.0→91.9 cm), COM vertical excursion (8.7→8.0→7.3 cm), IC COM–heel distance (9.2→7.8→7.0 cm), peak knee flexion (46.3→44.1→42.8°), peak hip adduction (10.4→9.5→8.7°), knee energy absorption; all P < 0.01 (Tables 1–3). Mechanistic, not an injury outcome study. |
| Malisoux 2023 | 860 healthy recreational runners (529 M / 331 F), age 40.2 ± 10 | preferred speed 9.9 ± 1.5 km/h (M 10.5, F 9.0) | instrumented treadmill | step rate 164 ± 9 steps/min (M 164 ± 10, F 164 ± 9) | Table 1 | Regression (Table 5): step rate = 203.056 + 0.193·age − 44.242·height(m) + 3.067·speed(km/h). Computed by us for age 40, 1.75 m: ≈164 at 10 km/h, ≈170 at 12, ≈176 at 14 km/h. Per-speed percentiles (Table 2) are an image; not retrievable. |
| Folland 2017 | 97 runners (47 F), 10 km bests 29:32–56:49 | 10–12 km/h | 3D, treadmill | stride rate 89.0 ± 8.5 strides/min (= 178 ± 17 steps/min) | Table 2 (full text) | Higher stride rate correlated with better energy cost, r = −0.32. |
| Lieberman 2015 | 14 runners | 3.0 m/s | 3D + VO2 | metabolically optimal 84.8 ± 3.6 strides/min (≈170 steps/min); foot position relative to hip fell 5.9 % per +5 strides/min | abstract | Economy, not injury. |
| Van Hooren 2024 | meta-analysis, 37 studies / 593 participants | various | — | cadence vs oxygen/energy cost r = −0.20 (95 % CI −0.35 to −0.05) | abstract / results | "small significant association"; moderate certainty. |

**Proposed Typical Range for the app: 160–180 steps/min at 10–14 km/h (speed-dependent; expect ~+3 steps/min per km/h).** Reasoning: large recreational cohort mean 164 ± 9 at ~10 km/h; faster/trained cohort 178 ± 17 at 10–12 km/h; the +5–10 % intervention logic (Heiderscheit) applies relative to the runner's own preferred cadence, not to an absolute number. Confidence: **high** for the descriptive range, **medium** for any benefit claim.

---

## 2. Overstride (heel/ankle ahead of hip at IC; tibia angle at IC)

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Heiderscheit 2011 | 45 recreational | 2.9 m/s | 3D treadmill | "IC COM – Heel Distance" 9.2 ± 4.0 cm (preferred); 11.4 ± 4.2 (−10 %); 7.0 ± 3.9 (+10 %) | Table 1 | Reduced with higher cadence together with braking impulse. |
| Souza 2016 | clinical 2D protocol (review) | treadmill | 2D lateral video, ≥120 Hz recommended | Tibia angle: "extended" when knee is posterior to the ankle (overstriding), "vertical", or "flexed"; no numeric threshold | text, "Tibia Angle at Loading Response" | Qualitative only; states vertical/flexed tibia dissipates impact better. |
| Sacroiliac-pain 2D study (J Phys Ther Sci 2022) | 63 female runners without SI pain vs 18 with | ≥4 mph treadmill | 2D video | tibial overstride angle 6.4 ± 4.4° (no pain) vs 10.0 ± 2.2° (pain), p < 0.05 | Table 2 | Small clinical sample; females only. |
| Adolescent 2D normative study (HSS, 2024) | 53 healthy competitive runners 14–18 y (51 % boys) | not reported in abstract | 2D video (Dartfish) | tibia inclination at IC 8.5 ± 3.2° | abstract only | Adolescents, not adults. |
| Folland 2017 | 97 runners | 10–12 km/h | 3D treadmill | shank angle at touchdown 75.0 ± 6.5° (angle to horizontal, i.e. ≈15° from vertical, foot ahead of knee) | Table 2 | Larger shank/foot touchdown angles related to worse performance; shank angle entered the performance model (31 %). |
| Lieberman 2015 | 14 runners | 3.0 m/s | 3D | greater anterior foot landing position → higher braking force; recommends "relatively vertical tibia" | abstract | Economy/braking mechanism; no injury outcome. |
| IJSPT 2023 categorical 2D | 33 recreational | self-selected | 60 fps phone | category "aligned with the pelvis" vs "anterior to the pelvis"; κ 0.78–0.92 | text/table | Most reliable 2D category; no numeric cut-off. |
| Bramah 2018 | 72 injured / 36 healthy | see §3 | 3D | injured ran with "an extended knee and dorsiflexed ankle at initial contact" (abstract); numeric foot-ahead-of-hip distance not found | abstract | Cross-sectional; cannot separate cause from effect. |

**Proposed Typical Range for the app: heel ≈ 5–13 cm ahead of hip/COM at IC (3D: 9.2 ± 4.0 cm); tibia angle at IC ≈ 2–11° ahead of vertical (2D: 6.4 ± 4.4°, 8.5 ± 3.2°); flag > ~12–15° or heel > ~15 cm as "overstriding".** Reasoning: only one 3D cohort gives a distance; 2D angle norms come from two small female/adolescent samples. Confidence: **low–medium**.

---

## 3. Knee flexion at initial contact

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Bramah 2018 | 72 injured (18 each PFP, ITBS, MTSS, AT) vs 36 healthy | not confirmed in retrieved text | 3D | knee flexion at IC: healthy 10.2 ± 4.8°, injured 6.0 ± 4.9°; effect size 0.87 | results table, via search-engine excerpt of SAGE full text (verify against Table 2) | Injured = more extended knee at IC; cross-sectional. |
| Heiderscheit 2011 | 45 recreational | 2.9 m/s | 3D treadmill | "IC Flexion Angle" 17.8 ± 4.0°; peak stance flexion 46.3 ± 4.5° | Table 3 | Different marker/model conventions give higher values than Bramah. |
| Adolescent 2D normative study | 53 adolescents | n/r | 2D video | knee flexion at IC 13.2 ± 3.8°; peak 44.5 ± 3.6° | abstract only | — |
| Sacroiliac-pain 2D study 2022 | 63 females | ≥4 mph | 2D video | knee angle at IC 163.7 ± 6.5° (≈16° flexion) | Table 2 | — |
| Folland 2017 | 97 runners | 10–12 km/h | 3D | minimum knee angle during contact 22.4 ± 9.3° (their variable is the included angle minimum, i.e. peak flexion proxy); r = −0.53 with energy cost | Table 2 | Entered the 39 % economy model (9.2 %). |
| Souza 2016 | review | — | 2D | "normal peak knee flexion approaches approximately 45° at midstance"; "lower knee flexion (<40°) may be associated with certain subgroups of patients with patellofemoral pain" | text, "Knee Flexion During Stance" | No numeric norm for IC itself. |

**Proposed Typical Range for the app: 8–20° knee flexion at IC (centre ≈ 10–18°); peak stance flexion ≈ 40–50°.** Reasoning: healthy 3D means 10.2 and 17.8°, 2D 13.2 and ~16°; injured groups cluster around 6° (Bramah). Confidence: **medium** (range), **low** for any injury cut-off.

---

## 4. Foot angle at IC / foot-strike pattern

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Altman & Davis 2012 | 20 runners (sex/age not retrieved) | overground over force plate | 3D + force plate, shod and barefoot | foot strike angle thresholds: FFS < −1.6°, MFS −1.6 to 8.0°, RFS > 8.0°; angle "significantly correlated with strike index" | abstract + secondary sources (IJSPT 2D/3D agreement paper quotes the cutoffs); group means ± SD not found (full text inaccessible) | Classification tool; no injury outcome. |
| IJSPT 2D vs 3D agreement study | 4 male recreational runners, 162 foot strikes | 2.1–3.5 m/s overground | 2D 240 fps visual vs 3D angle | RFS vs non-RFS κ = 0.95 [0.90, 1.00]; three categories κ = 0.71 [0.62, 0.80] | results | 2D reliably separates RFS from non-RFS; MFS vs FFS less reliable. |
| Larson 2011 | 936 recreational and sub-elite runners, road race | race pace at 10 km | 2D video | 88.9 % RFS, 3.4 % MFS, 1.8 % FFS, 5.9 % asymmetric; RFS share higher at 32 km | abstract | Observational. |
| Hasegawa 2007 | 283 analysed of 415 elite half-marathoners | ~15 km point of race (top 50 ≈ 5.45 m/s) | 2D 120 Hz video | 74.9 % RFS, 23.7 % MFS, 1.4 % FFS; top-50: 62.0 / 36.0 / 2.0 % | abstract | Faster runners → more MFS. |
| Folland 2017 | 97 runners | 10–12 km/h | 3D | foot angle at touchdown 16.8 ± 7.3° | Table 2 | Greater foot angle at touchdown related to worse performance. |
| Adolescent 2D study / SI-pain 2D study | 53 adolescents / 63 females | — | 2D | foot inclination at IC 10.2 ± 6.2° / 9.2 ± 4.5°; 91 % RFS (adolescents) | abstract / Table 2 | — |
| Ogueta-Alday 2014 | 20 sub-elite (10 RFS, 10 MFS) | 11, 13, 15 km/h treadmill | contact platform + VO2 | RFS 5.4 %, 9.3 %, 5.0 % more economical than MFS (n.s. at 15 km/h) | abstract | Changing strike pattern is not supported as an economy gain. |

**Proposed Typical Range for the app: classify by foot angle at IC using Altman & Davis cutoffs (RFS > 8°, MFS −1.6…8°, FFS < −1.6°); expect ~75–90 % of recreational runners to be RFS, with typical RFS foot angle ≈ 9–17°.** Confidence: **high** for the cutoffs and RFS prevalence; **low** for any "better" pattern (no injury or economy advantage established).

---

## 5. Vertical oscillation (cm)

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Heiderscheit 2011 | 45 recreational | 2.9 m/s | 3D COM, treadmill | COM vertical excursion 8.7 ± 1.3 cm (preferred); 10.7 ± 1.5 (−10 % cadence); 7.3 ± 1.1 (+10 %) | Table 1 | — |
| Malisoux 2023 | 860 recreational | ~10 km/h preferred | instrumented treadmill | VO 77 ± 12 mm (M 80 ± 13, F 73 ± 11) | Table 1 | Largest reference cohort; VO definition from force-plate integration. |
| Folland 2017 | 97 runners | 10–12 km/h | 3D pelvis | pelvis VO during ground contact 0.054 ± 0.015 × height; total pelvis VO 0.088 ± 0.021 × height (≈9 cm and ≈15 cm for 1.70 m, computed by us) | Table 2 | VO during contact r = 0.534 with energy cost; strongest single predictor (27.7 % of 39 % model). Pelvis VO > COM VO, so values are not interchangeable. |
| Tartaruga 2012 | 16 homogeneous male distance runners | 4.4 m/s | lab | "significant correlations between RE and … vertical oscillation of the center of mass" | abstract only; r and cm values not found | — |
| Van Hooren 2024 | 23 studies / 317 participants | various | meta | VO vs oxygen/energy cost r = 0.35 (0.19 to 0.49) | abstract / results | "moderate" association; moderate certainty. |

**Proposed Typical Range for the app: 6–10 cm pelvis/COM VO at 10–12 km/h (centre ≈ 8 cm); lower is weakly better for economy.** Reasoning: 7.7 ± 1.2 cm (n = 860) and 8.7 ± 1.3 cm (n = 45) agree; a 2D hip-marker estimate will sit closer to pelvis VO (higher than COM). Confidence: **medium** (definition- and method-dependent).

---

## 6. Trunk forward lean at midstance

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Teng & Powers 2014 | 24 asymptomatic recreational runners (12 F / 12 M) | 3.4 m/s overground | 3D | self-selected trunk flexion 7.3 ± 3.6°; flexed 14.1 ± 4.8°; extended 4.0 ± 3.9°; peak PFJ stress 20.2 ± 3.4 MPa flexed vs 23.1 ± 3.4 MPa extended | abstract | More lean lowers PFJ stress (modelling); no injury outcome. |
| Folland 2017 | 97 runners | 10–12 km/h | 3D | trunk forward lean (mean) −7.8 ± 4.5° (sign convention: negative = forward) | Table 2 | Weak relation to performance; entered the performance model. |
| Bramah 2018 | 72 injured / 36 healthy | — | 3D | injured had "greater … forward trunk lean at midstance" (abstract); degrees not retrieved | abstract | Direction conflicts with Teng's PFJ-stress logic; cross-sectional. |
| Sacroiliac-pain 2D study 2022 | 63 females | ≥4 mph | 2D | trunk posture angle 4.1 ± 2.8° | Table 2 | 2D definition differs (segment vs vertical). |
| Souza 2016 | review | — | 2D | numeric norm not found in retrievable sections (remainder paywalled); secondary teaching material cites "5–7.5° recreational, ~3° elite" but the primary source for those numbers was not confirmed | — | treat as unverified. |

**Proposed Typical Range for the app: 4–12° forward lean of trunk from vertical at midstance (centre ≈ 7–8°).** Reasoning: two 3D cohorts give 7.3 ± 3.6° and 7.8 ± 4.5°; 2D lower (4.1 ± 2.8°). Confidence: **medium** for the range, **low** for direction of benefit (injured runners lean more in Bramah; more lean reduces PFJ stress in Teng).

---

## 7. Ground contact time and flight time (10–14 km/h)

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Folland 2017 | 97 runners | 10–12 km/h | 3D treadmill | GCT 0.281 ± 0.032 s; swing time 0.242 ± 0.038 s; duty factor 0.538 ± 0.043 | Table 2 | GCT "not associated with LEc" (text), but related to performance. |
| Malisoux 2023 | 860 recreational | ~10 km/h | instrumented treadmill | contact time 289 ± 35 ms (M 283 ± 33, F 299 ± 36); "flight time" 444 ± 38 ms (note: contact + 444 ≈ stride time at 164 steps/min, so this is a swing/non-contact time per leg, not aerial time); contact time = 259.01 + 12.8·sex + 0.855·mass + 77.122·height − 17.314·speed(km/h) | Table 1, Table 5 | ≈ −17 ms per km/h. |
| Hasegawa 2007 | 283 elite half-marathoners | ≈5.4–5.5 m/s (top 50) | 2D 120 Hz | contact time RFS 200.0 ± 21.3 vs MFS+FFS 183.0 ± 16 ms; CT increased in slower runners (r = 0.71) | abstract | Much faster than app speeds. |
| Ogueta-Alday 2014 | 20 sub-elite | 11/13/15 km/h treadmill | contact platform | RFS longer contact time and shorter flight time than MFS at all speeds (P < 0.01); ms values not found (table not accessible) | abstract | — |
| Van Hooren 2024 | 40 / 591 (GCT), 18 / 242 (flight) | — | meta | GCT r = −0.02 (−0.15 to 0.12); flight time r = 0.11 (−0.09 to 0.32); duty factor r = −0.06 | results | Trivial/non-significant; high certainty for duty factor and flight time. |

**Proposed Typical Range for the app: GCT 250–320 ms at 10–12 km/h, ~230–300 ms at 14 km/h (≈ −17 ms per km/h); true aerial (flight) time per step ≈ 80–130 ms at these speeds is a derived estimate (step time 330–375 ms minus GCT) — direct norms not found.** Show as descriptive only: no association with economy (Van Hooren) and no prospective injury evidence. Confidence: **medium** (GCT), **low** (flight time).

---

## 8. Contralateral pelvic drop at midstance

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Bramah 2018 | 72 injured / 36 healthy, mixed injuries | — | 3D | CPD healthy 3.7 ± 1.9°, injured 6.4 ± 2.1°; effect size 1.37; "for every 1° increase in pelvic drop there was an 80 % increase in the odds of being classified injured"; pattern consistent across PFP, ITBS, MTSS, AT | abstract (odds) + results table via search excerpt of SAGE full text | Cross-sectional: cannot prove CPD causes injury. Strongest single variable in the model. |
| Maykut 2015 | 24 collegiate XC runners (14 M / 10 F), 64 mi/wk | self-selected treadmill | 2D 60 Hz vs 3D 240 Hz | CPD 2D 4.6 ± 2.1° / 4.3 ± 1.9° (R/L); 3D 5.2 ± 1.4° / 5.7 ± 2.1°; intra-rater ICC 0.958–0.966 | Table 2–3 | 2D reliable; slight underestimate vs 3D. |
| Sacroiliac-pain 2D study 2022 | 63 females (no pain) / 18 (pain) | ≥4 mph | 2D | CPD 5.22 ± 2.6° vs 7.8 ± 3.8°, p < 0.01 | Table 3 | — |
| Adolescent 2D study | 53 adolescents | — | 2D | CPD 6.0 ± 2.2° | abstract only | — |
| Dingenen 2018 | 21 recreational runners | — | 2D | CPD among variables with acceptable test-retest reliability; ICC/SEM values not retrieved | abstract | — |
| IJSPT 2023 categorical 2D | 33 recreational | — | 2D 60 fps | pelvic drop κ 0.05–0.60 (lowest of nine items) | table | Categorical rating of CPD is unreliable between raters; measure the angle instead. |
| Heiderscheit 2011 | 45 recreational | 2.9 m/s | 3D | +10 % cadence reduced peak hip adduction angle (P < 0.01); CPD not reported | Table 3 | — |
| Souza 2016 | review | — | 2D | no numeric threshold found | — | — |

**Proposed Typical Range for the app: 2–7° CPD at midstance (healthy centres 3.7–6.0°); flag ≥ ~7–8° as "elevated".** Reasoning: healthy means 3.7 (3D), 4.3–5.7 (2D/3D), 5.2 and 6.0 (2D); injured means 6.4–7.8°. Confidence: **medium** for the range, **medium** for association (consistent across injuries but cross-sectional).

---

## 9. Hip adduction at midstance

| Source | Population | Speed | Method | Value | Where stated | Evidence note |
|---|---|---|---|---|---|---|
| Bramah 2018 | 72 injured / 36 healthy | — | 3D | hip adduction healthy 9.7 ± 3.5°, injured 13.0 ± 3.9°; effect size 0.89 | results table via search excerpt | Cross-sectional. |
| Heiderscheit 2011 | 45 recreational | 2.9 m/s | 3D | peak hip adduction 10.4 ± 3.3° (preferred); 8.7° at +10 % cadence | Table 3 | — |
| Maykut 2015 | 24 collegiate XC | self-selected | 2D vs 3D | 2D 11.2 ± 2.7° / 11.8 ± 2.7°; 3D 14.0 ± 3.7° / 13.8 ± 2.5°; r = 0.62 / 0.54 | Table 3 | 2D underestimates 3D by ~2–3°. |
| Sacroiliac-pain 2D study 2022 | 63 females | ≥4 mph | 2D | 7.5 ± 2.4° (no pain) vs 8.0 ± 1.7° (pain), n.s. | Table 3 | — |
| Noehren 2013 | 400 healthy females followed 2 y; 15 PFP vs 15 controls, age 27 ± 10 | 3.7 m/s | 3D | PFP group "significantly greater hip adduction (P = 0.007)"; hip IR P = 0.47; rearfoot eversion P = 0.1; degree values not found (abstract only) | abstract | Prospective — strongest design for this metric. |
| Noehren 2007 | prospective; 18 females who developed ITBS vs matched controls | — | 3D | ITBS group "significantly greater hip adduction and knee internal rotation"; rearfoot eversion and knee flexion similar; degrees not found | abstract | Prospective. |
| Willson & Davis 2008 | 20 PFPS (5 M / 15 F) vs 20 controls | prolonged treadmill run | 3D | hip abduction strength lower in PFPS (15.3→13.5 vs 17.3→15.4 kg·cm/BM); strength vs peak hip adduction r = −0.74 at end of run; adduction degrees not in abstract | abstract | Cross-sectional. |
| Ceyssens 2019 | review | — | — | "limited evidence" for greater peak hip adduction in females developing PFP and ITBS; not in mixed-sex XC runners | abstract | — |

**Proposed Typical Range for the app: 2D hip adduction ≈ 6–13° at midstance (3D ≈ 8–14°); flag > ~14° (2D) as "elevated".** Reasoning: 2D healthy means 7.5 and 11–12°; 3D 9.7–14°; injured 3D 13°. Confidence: **medium** for the range; **medium** for injury association (two prospective female studies, limited evidence per Ceyssens).

---

## 10. Rearfoot eversion / pronation — excluded

- **Why excluded in the app:** 2D pose keypoints give no reliable calcaneus or shoe-heel
  landmark from a posterior view, and rearfoot eversion is a small (few degrees), fast
  frontal-plane motion that is sensitive to camera alignment; the 2023 IJSPT categorical study
  found heel eversion among the least reliable 2D items (κ 0.24–0.60).
- **What the literature says:** Nielsen 2014 (927 novice runners, neutral shoe, 1-year
  prospective cohort): foot pronation (Foot Posture Index) was not associated with increased
  injury risk; e.g. highly supinated feet RD = 11.0 % (−10 % to 32.1 %), p = 0.30 after 250 km
  (abstract). Malisoux 2016 (RCT, n = 372, 6 months): motion-control shoes lowered overall
  injury risk, HR = 0.55 (95 % CI 0.36–0.85), with the effect confined to runners with pronated
  feet (abstract). Malisoux 2020 (RCT, n = 848): harder (less cushioned) shoes raised injury
  risk, HR = 1.52 (1.07–2.16), only in lighter runners (HR 1.80 [1.09–2.98]). Noehren 2007/2013:
  rearfoot eversion did not differ prospectively in ITBS or PFP groups. Net: pronation per se is
  a weak/unsupported injury predictor; footwear interactions exist but are not video-measurable.

---

## Sources

- Altman AR, Davis IS. A kinematic method for footstrike pattern detection in barefoot and shod runners. Gait Posture 2012;35:298–300. doi:10.1016/j.gaitpost.2011.09.104 (PMID 22075193)
- Bramah C, Preece SJ, Gill N, Herrington L. Is there a pathological gait associated with common soft tissue running injuries? Am J Sports Med 2018;46:3023–3031. doi:10.1177/0363546518793657 (PMID 30193080)
- Ceyssens L, Vanelderen R, Barton C, Malliaras P, Dingenen B. Biomechanical risk factors associated with running-related injuries: a systematic review. Sports Med 2019;49:1095–1115. doi:10.1007/s40279-019-01110-z
- Dingenen B, et al. Test-retest reliability of two-dimensional video analysis during running. Phys Ther Sport 2018;33:40–47. doi:10.1016/j.ptsp.2018.06.009
- Folland JP, Allen SJ, Black MI, Handsaker JC, Forrester SE. Running technique is an important component of running economy and performance. Med Sci Sports Exerc 2017;49:1412–1423. doi:10.1249/MSS.0000000000001245 (PMC5473370)
- Hasegawa H, Yamauchi T, Kraemer WJ. Foot strike patterns of runners at the 15-km point during an elite-level half marathon. J Strength Cond Res 2007;21:888–893. doi:10.1519/R-22096.1
- Heiderscheit BC, Chumanov ES, Michalski MP, Wille CM, Ryan MB. Effects of step rate manipulation on joint mechanics during running. Med Sci Sports Exerc 2011;43:296–302. doi:10.1249/MSS.0b013e3181ebedf4 (PMC3022995)
- Larson P, et al. Foot strike patterns of recreational and sub-elite runners in a long-distance road race. J Sports Sci 2011;29:1665–1673. doi:10.1080/02640414.2011.610347
- Lieberman DE, Warrener AG, Wang J, Castillo ER. Effects of stride frequency and foot position at landing on braking force, hip torque, impact peak force and the metabolic cost of running in humans. J Exp Biol 2015;218:3406–3414. doi:10.1242/jeb.125500
- Malisoux L, Chambon N, Delattre N, Gueguen N, Urhausen A, Theisen D. Injury risk in runners using standard or motion control shoes: a randomised controlled trial with participant and assessor blinding. Br J Sports Med 2016;50:481–487. doi:10.1136/bjsports-2015-095031
- Malisoux L, Delattre N, Urhausen A, Theisen D. Shoe cushioning influences the running injury risk according to body mass: a randomized controlled trial involving 848 recreational runners. Am J Sports Med 2020;48:473–480. doi:10.1177/0363546519892578
- Malisoux L, et al. Reference values and determinants of spatiotemporal and kinetic variables in recreational runners. Orthop J Sports Med 2023;11(10). doi:10.1177/23259671231204629 (PMC10588426)
- Maykut JN, Taylor-Haas JA, Paterno MV, DiCesare CA, Ford KR. Concurrent validity and reliability of 2D kinematic analysis of frontal plane motion during running. Int J Sports Phys Ther 2015;10:136–146. (PMC4387721)
- Nielsen RO, et al. Foot pronation is not associated with increased injury risk in novice runners wearing a neutral shoe: a 1-year prospective cohort study. Br J Sports Med 2014;48:440–447. doi:10.1136/bjsports-2013-092202
- Noehren B, Davis I, Hamill J. ASB Clinical Biomechanics Award Winner 2006: prospective study of the biomechanical factors associated with iliotibial band syndrome. Clin Biomech 2007;22:951–956. doi:10.1016/j.clinbiomech.2007.07.001
- Noehren B, Hamill J, Davis I. Prospective evidence for a hip etiology in patellofemoral pain. Med Sci Sports Exerc 2013;45:1120–1124. doi:10.1249/MSS.0b013e31828249d2
- Ogueta-Alday A, Rodríguez-Marroyo JA, García-López J. Rearfoot striking runners are more economical than midfoot strikers. Med Sci Sports Exerc 2014;46:580–585. doi:10.1249/MSS.0000000000000139
- Pipkin A, Kotecki K, Hetzel S, Heiderscheit B. Reliability of a qualitative video analysis for running. J Orthop Sports Phys Ther 2016;46:471–476. doi:10.2519/jospt.2016.6280
- Souza RB. An evidence-based videotaped running biomechanics analysis. Phys Med Rehabil Clin N Am 2016;27:217–236. doi:10.1016/j.pmr.2015.08.006 (PMC4714754)
- Tartaruga MP, et al. The relationship between running economy and biomechanical variables in distance runners. Res Q Exerc Sport 2012;83:367–375. doi:10.1080/02701367.2012.10599870
- Teng HL, Powers CM. Sagittal plane trunk posture influences patellofemoral joint stress during running. J Orthop Sports Phys Ther 2014;44:785–792. doi:10.2519/jospt.2014.5249
- Van Hooren B, Jukic I, Cox M, Frenken KG, Bautista I, Moore IS. The relationship between running biomechanics and running economy: a systematic review and meta-analysis of observational studies. Sports Med 2024;54:1269–1316. doi:10.1007/s40279-024-01997-3 (PMC11127892)
- Wille CM, Lenhart RL, Wang S, Thelen DG, Heiderscheit BC. Ability of sagittal kinematic variables to estimate ground reaction forces and joint kinetics in running. J Orthop Sports Phys Ther 2014;44:825–830. doi:10.2519/jospt.2014.5367
- Willson JD, Davis IS. Proximal and distal influences on hip and knee kinematics in runners with patellofemoral pain during a prolonged run. J Orthop Sports Phys Ther 2008;38:448–456. doi:10.2519/jospt.2008.2490
- Running gait biomechanics in female runners with sacroiliac joint pain (2D treadmill study). J Phys Ther Sci 2022. (PMC8989488) — authors not retrieved.
- Normative running kinematics in healthy adolescent runners: a 2-dimensional video analysis (Hospital for Special Surgery). https://vivo.weill.cornell.edu/display/pubid39108456 — journal/DOI not retrieved.
- Reliability of the main 2D kinematic variables of running evaluated categorically in amateur runners aged 18 to 55 years. Int J Sports Phys Ther 2023. https://ijspt.scholasticahq.com/article/142061
- Agreement between 2D visual and 3D motion capture based assessment of foot strike pattern. Int J Sports Phys Ther 2024. https://ijspt.scholasticahq.com/article/123952
