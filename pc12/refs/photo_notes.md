# PC-12 PRO cockpit glazing: what the photos show

These notes check the cockpit glazing (`model/cockpit_glazing.py`) against 26 real photographs listed in
`refs/photos.json`. The images themselves are not in git. `python3 refs/fetch_photos.py` downloads them into
`refs/cache/photos/`, which is gitignored. Photo ids below refer to the manifest.

**How each photo's variant was checked.** A photo counts as PRO only when a caption, article or visible
marking ties it to a PC-12 PRO serial:

| Serial | Registration | Evidence |
|---|---|---|
| s/n 3001 | HB-FSG | Commons caption and category; registration on the fin |
| s/n 3005 | | Pilatus article text |
| s/n 3008 | N81DW | article, plus "3008" on the nose-gear door |
| s/n 3010 | | RFDS article text |
| s/n 3036 | | "3036" on the nose-gear door |
| s/n 3066 | | "3066" on the nose-gear door, plus "PC-12 PRO" lettering on the nose and winglet |

NGX photos carry an NGX serial (c/n 2xxx), NGX lettering, or a caption. Two top views stay `unknown`.

**The "Kenia" photos are an NGX, not a PRO.** Pilatus names two files "PC-12-PRO-Kenia" and uses them on its
PC-12 PRO page. However, the starboard winglet in the photo reads **"PC-12 NGX"**, whereas PRO winglets read
"PC-12 PRO" (`pro3066_winglet_pilatus`). They are therefore listed as NGX (`ngx_kenia_*`). The starboard
glazing is the same on both variants (see (a)), so they are still used for side-view geometry.

**Which side a photo shows.** In a side view, the nose pointing left in the image means the port (left) side is
visible. The pilot sits on the port side.

Scratch evidence is in `out/tmp/photos/` (gitignored), under `evidence/` and `blender/`.

Measurement uncertainty: scale is about ±6 %, and absolute positions are about ±0.05–0.1 m. These are perspective
photos registered by hand; see the notes under each measurement. Ratios within one window are more reliable than
absolute values.

---------------------------------------------------------------------------------------------------------

## (a) PRO: the pilot's direct-vision (DV) window is gone. The port side window is one pane.

- **Pilatus release text** (news "pc-12-pro", 2025-03-14): *"Exterior visibility has been improved by removing
  the 'Direct Vision' cockpit window frame."*
- **NGX port side: the window is split into two panes.** The whole opening is the same trapezoid-plus-D outline
  as the starboard window, but a body-coloured **post** divides it:
  - a small **triangular DV pane** in the lower-front corner;
  - the D-ended **main pane** behind it.

  This is clear in `ngx_ownership_port_pilatus`, `ngx2157_hbfxa_port34`, `ngx2060_lxfli_port` and
  `ngx2202_tradewind_port34_pilatus`. It is visible but soft in `ngx_dfbox_port`. The side-by-side sheet is
  `evidence/port_windows_PRO_vs_NGX.jpg`.
  - Measured on `ngx_ownership_port_pilatus`, which is close to broadside. The open airstair door is the scale
    bar: 110 × 250 px for 0.61 × 1.35 m, giving about 182 px/m.
  - **Triangular DV pane:**
    - its hypotenuse lies on the A-pillar line;
    - its base runs along the sill for 0.24–0.27 m;
    - its top vertex is about 0.16 m above the sill (about 40 % of the glass height).
  - **Post:** about 0.06 m wide. It runs from that vertex down to the sill, with its foot leaning aft by roughly 20°.
- **PRO port side: a single pane with no post.** Its outline is the same as the starboard pane. The glass runs
  straight from the A-pillar to the D-shaped aft end, as seen in:
  - `pro3001_port_close_aero25` (s/n 3001);
  - `pro3010_rfds_port_pilatus` (s/n 3010);
  - `pro3036_port34_pilatus`, `pro3066_port34_pilatus`, `pro3008_port34_pilatus` and
    `pro3005_port_close_pilatus`;
  - `pro3001_air_port34_pilatus` (air-to-air).

  Proportions match the starboard window within the measurement scatter:

  | photo | side, variant | sill length ÷ height | top length ÷ height | front-edge angle |
  |---|---|---|---|---|
  | `ngx_kenia_stbd_pilatus` (broadside) | stbd, NGX | 2.09 | 0.85 | 36° |
  | `ngx2243_hbfxk_stbd` (close, wide-angle) | stbd, NGX | 1.98 | 0.71 | 32° |
  | `ngx_ownership_port_pilatus` (DV + main pane together) | port, NGX | 2.04 | 0.72 | 33.5° |
  | `pro3010_rfds_port_pilatus` (front quarter, ~20° foreshortened) | port, PRO | 2.04 raw (≈2.2 corrected) | ≈1.0 | 39° |
  | `pro3001_stbd_side_aero25` (from ahead, ~65 px window) | stbd, PRO | 1.77 (foreshortened) | 0.51 | 35° |
  | model `cockpit_glazing.py` | — | 2.06 | 1.07 | 45° |

  "Sill length" runs from the front-bottom corner to the aft extreme. "Top length" runs from the top-front corner
  to the aft extreme. "Front-edge angle" is the image-plane slope of the A-pillar edge above horizontal.

**Conclusion:** yes. On the PRO, the port side window is one pane of the same shape as the starboard one: a
mirror image, with no DV frame. The model's `glazing_flightdeck` note ("no DV window, PRO") is consistent with this.

## (b) Side-window shape

Every photo, on both sides and both variants, shows the same shape (see `evidence/stbd_windows.jpg`):

- **Front edge:** a straight line that is the side-window edge of the **A-pillar**. It runs parallel to the
  windshield's outboard edge and slopes down and forward at **about 32–39°** in near-broadside views. The model
  uses 45°.
  - The A-pillar between windshield glass and side glass is narrow: about 0.05–0.06 m in side view
    (`ngx_kenia_stbd_pilatus`, `ngx_ownership_port_pilatus`).
  - The top-front corner is acute, with a small radius. The front-bottom corner has a small radius, about 0.02–0.03 m.
- **Sill:** straight and horizontal in broadside views (`ngx_kenia_stbd_pilatus`, `ngx2243_hbfxk_stbd`,
  `pro3010_rfds_port_pilatus`).
- **Top edge:** straight and short, nearly horizontal (rising forward by at most a few mm per 0.1 m). It is only
  about 0.3–0.35 m long because the sloping pillar consumes the front.
- **Aft edge:** a large-radius, rounded **"D"**:
  - a short straight vertical segment (about 0.17 m);
  - top-aft and bottom-aft corner radii of about **0.11–0.14 m** (roughly 0.3 × the glass height).

  It is *not* the near-square corner of the model (`smax` k = 0.05).
- **Size and position.** Measured on `ngx_kenia_stbd_pilatus` at 5000 px, near broadside:
  - Registration: spinner tip = STA 0.39, prop axis = WL 1.655, and the aft cowling joint taken as the
    firewall, STA 3.00.
  - The two horizontal checks both give **166 px/m**: spinner tip to cowl joint (2.61 m), and the 3.48 m
    three-view wheelbase (≈167 px/m).
  - Vertical check: the visible tyre bottoms come out about 0.1 m above WL 0. The wheels stand in grass on a dirt
    strip, so treat WLs as ±0.1 m.

  | glass point | photo (STA, WL) | model constraint |
  |---|---|---|
  | aft extreme | 4.34, 2.29 | `SW_REAR` 4.268 |
  | sill | WL 2.11 (STA 3.54–4.23) | `SW_BOTTOM` 1.985 |
  | top edge | WL 2.51 | `SW_TOP` 2.445–2.475 |
  | top-front corner | 4.00, 2.51 | ≈ 3.76, 2.44 |
  | front-bottom corner | 3.51, 2.155 | ≈ 3.30, 1.985 |
  | glass height / sill length / top length | 0.40 / 0.83 / 0.34 m | 0.46–0.49 / 0.97 / 0.51 m |

  - An independent check on `ngx_ownership_port_pilatus`, using the door as scale, gives height 0.40 m, sill
    length 0.81 m and top length 0.29 m.
  - Overlay: `evidence/model_vs_photo_stbd_window.jpg`. Red is the model's `sidewindow_sdf = 0`, cyan is the glass
    measured on the photo. The model window sits about 0.12 m too low at the sill, and its lower-front corner is
    about 0.2 m too far forward and low. Its pillar is too steep, and its aft end is too square.
- **Relative to the cabin windows** (same photos):
  - The cockpit glass sill is **0.30–0.39 cabin-window heights above the cabin-window bottom edge**, roughly
    0.1–0.14 m (`ngx_kenia_stbd_pilatus` 18 px; `ngx2243_hbfxk_stbd` 40 px).
  - The glass top is 0.38–0.54 cabin-window heights above the cabin-window top.
  - The glass height is 1.08–1.16 × the cabin-window height.
  - The glass sill length is about 2.8 × the cabin-window width.
- **Scale-bar caution.** The cabin windows measure about **w/h = 0.78–0.82** (49×61, 84×103 and 66×85 px), with a
  visible height of about **0.36 m**. That figure comes from two independent scales: 166 px/m on
  `ngx_kenia_stbd_pilatus`, and the door height on `pro3010_rfds_port_pilatus`. This is not the model's
  0.31 × 0.43 m, so the airstair door (0.61 × 1.35 m) is the safer scale bar.

## (c) Windshield

- **Two panes and a centre post**, in `unk_top_front_pilatus`, `pro3001_stbd34_close_aero25`,
  `unk_top_corsica_pilatus` and `pro_mexico_front_pilatus`.
- **Pane outline.** Seen from high front (`unk_top_front_pilatus`), each pane is a four-sided, round-cornered pane:
  - the roof edge and the lower edge run almost straight across, the roof edge as a shallow curve over both panes;
  - the inboard edge is straight along the post;
  - the outboard edge curves back to meet the A-pillar.
- **How the panes wrap.** Seen from the side (`ngx_kenia_stbd_pilatus`), the pane wraps around the nose corner.
  Only a thin sliver shows ahead of the pillar:
  - Its lower edge is almost horizontal at WL ≈ 2.13–2.21.
  - Its roof edge falls forward at about 25°, from about (STA 3.93, WL 2.57) at the pillar top to the forward tip
    at about **STA 3.2, WL 2.2**. The model's windshield sill (`cockpit_glazing.SILL_LINE`, tip at the crown STA ~3.27) matches.
  - The roof edge meets the pillar about 0.1–0.17 m further aft than the model's roof line at x = 3.832. This is
    only an estimate from a side projection.
- **Centre post.** On dark-surround aircraft the post looks like a dark riveted band (`pro3001_stbd34_close_aero25`).
  - The glass-to-glass gap is about **¼ of one pane's projected width** in `unk_top_front_pilatus` (37 px vs
    142 px), and about 0.15 in the ¾ view `pro3001_stbd34_close_aero25`.
  - That suggests roughly 0.08–0.14 m between glass edges, against the model's 2 × `WS_POST` = 0.068 m.
    Treat this as indicative only.
- **Head-on** (`pro3001_front_aero25`): the panes wrap well round the nose sides. A narrow black band runs along the
  roof edge above both panes. The spinner and blade hide the lower edge and the post.
- An unidentified light-coloured vertical fitting or reflection lies along the inboard edge of the port pane in
  `ngx_kenia_port34_pilatus`. It is not interpreted here.

## (d) The dark windshield surround ("mask")

- **It is a paint feature, not a variant feature.**
  - **Every PRO photographed has one:**
    - black on s/n 3001, 3010, 3036 and 3066;
    - dark navy or black on the blue s/n 3008;
    - **red with a black keyline**, larger than on the others, on s/n 3005 (`pro3005_port_close_pilatus`).

    Its colour therefore follows the livery.
  - **NGX: some have one, most photographed here do not.** It is present in dark navy or blue on the
    `ngx_kenia_*` aircraft. It is absent on:
    - HB-FXK, D-FFMK, HB-FXA, LX-FLI and s/n 2202;
    - the Pilatus "Ownership" NGX;
    - the unknown-variant Corsica aircraft (`unk_top_corsica_pilatus`).

    On those aircraft the frames are body colour with only a thin dark seal line.

  This contradicts a blanket "NGX: dark windshield surround" (the CLAUDE.md sourced fact). It is at most an option
  or livery element on the NGX.
- **Finish.** Gloss, with rivet heads visible along the frames (`pro3001_port_close_aero25`,
  `pro3066_port34_pilatus`, `pro3001_stbd34_close_aero25`). On unpainted NGX HB-FXK, rows of rivets outline a frame
  around the side window with a straight aft edge and a horizontal lower edge (`evidence/ngx2243_stbd_riveted_frame.jpg`).
  This is consistent with the mask following the window-frame region, but the photos do not prove it.
- **Continuity.** It is **one continuous dark area** around all four panes:
  - The A-pillar is inside it on each side, so windshield and side window are joined (`pro3036_port34_pilatus`,
    `pro3010_rfds_port_pilatus`, `pro3001_port_close_aero25`).
  - A narrow band runs along the roof edge above the windshield (`pro3001_front_aero25`) and along its lower edge
    (`pro3001_stbd34_close_aero25`; the NGX `ngx_kenia_port34_pilatus`).
  - The centre post is dark (`pro3001_stbd34_close_aero25`).
- **Outline around the side window.** Measured on `ngx_kenia_stbd_pilatus`; the PRO photos show the same shape
  (`evidence/pro3036_surround_outline.jpg`).
  - **Aft edge:** straight and near-vertical, with small corner radii (about 0.02–0.05 m). It is *not* a D
    following the glass. In near-broadside views its lower end is 7–23° further forward than its top:
    `pro3010_rfds_port_pilatus` 7°, `ngx_kenia_stbd_pilatus` about 20°, `pro3001_stbd_side_aero25` about 23°.
    It runs from about STA 4.48 at the top to STA 4.30 at the bottom.
  - **On the port side, the aft edge stops at the forward frame of the airstair door**, within about 0.05 m
    (`pro3010_rfds_port_pilatus`, `pro3001_port_close_aero25`, `pro3036_port34_pilatus`).
  - **Correction (sheet-L2 review, 2026-09-24): the aft edge is a per-airframe livery item.** Rectified onto the
    OML with the camera fits (refs/cache/overlays/livery/cams.json), s/n 3008 (`pro3008_stbd34_pilatus`,
    `pro3008_port34_pilatus`) leans 22–27°: STA 4.385 at WL 2.10, 4.47 at 2.30, 4.515 at 2.40, ~4.55 at 2.50. On
    port a blue gap separates it from the door seam (~0.10 m at the top, ~0.27 m low). s/n 3036 has a vertical
    edge within ~0.05 m of the door frame; s/n 3010 leans ~12–16° (corrected against the door jamb); s/n 3066
    curves round the glass D. The model carries s/n 3008 (`model/livery.py` `MASK_SCHEMES`).
  - **Lower edge:** horizontal, about **0.06–0.08 m below the glass sill** (WL ≈ 2.03 on `ngx_kenia_stbd_pilatus`).
    Forward of the side window (from about STA 3.6) it ramps **up at about 23°** to a point at the windshield's
    lower-forward corner, at about **STA 3.17, WL 2.21**.
  - **Top edge:** the margin above the glass is small in side view (0–0.05 m). The edge rises slightly forward and
    merges into the windshield roof band.
  - **Aft margin** behind the glass: about 0.07 m at the bottom and 0.15–0.2 m at the top, because the aft edge
    leans. The model's surround is a uniform 0.034 m grow (smooth-min blended) whose lower-forward tab reaches further
    forward and lower than the real ramp (`blender/overlay_kenia_stbd_zoom.jpg`), so it does not match this outline.

## (e) Other features visible on the PRO

- **Lettering.**
  - "PC-12 PRO" on the winglets (`pro3066_winglet_pilatus`) and below the PILATUS logo on the nose
    (`pro3066_port34_pilatus`).
  - The NGX `ngx_kenia_*` winglet reads "PC-12 NGX" (`evidence/ngx_kenia_winglet_lettering.jpg`).
  - s/n 3001 carries "PC-12" and an "EXPERIMENTAL" placard (`pro3001_port_close_aero25`).
- **Winglets:** upturned, with a nav light on the top edge and static wicks, the same on the NGX
  (`pro3066_winglet_pilatus`, `ngx_kenia_stbd_pilatus`).
- **Weather radar.** Pilatus says the PRO radar has "a new and larger antenna". A starboard-wing radar pod is
  visible on NGX `ngx_kenia_stbd_pilatus`, but **no PRO/NGX pod size comparison was possible** from these photos.
- **Antennas:**
  - one larger swept blade on the crown just aft of the airstair door;
  - small blades and domes along the crown and above the cockpit;

  as seen in `pro3010_rfds_port_pilatus`, `pro3001_port_close_aero25` and `ngx_kenia_stbd_pilatus`.
- **Liveries:**
  - s/n 3001: metallic grey with orange and white geometric panels;
  - s/n 3036: silver with red and black stripes;
  - s/n 3010: RFDS white, red and blue;
  - s/n 3066: grey with orange;
  - s/n 3008: blue with white sweeps;
  - s/n 3005: red, white and blue.
- **Starboard cabin-window positions (outside glazing scope, flagged for the model).** On two NGX starboard views:
  - The first cabin window's centre lies **about 3.4 window widths (~1.0 m) aft of the cockpit glass's aft extreme**.
  - The window pitch is about 2.76 widths, and the next window is the one in the Type III exit.

  This holds on `ngx_kenia_stbd_pilatus` and `ngx2243_hbfxk_stbd`. It puts the first window near STA 5.3 and the
  exit window near STA 6.1–6.2. The model has 4.72 and 5.52, so the model row appears about 0.6 m too far forward.
  The Blender overlay shows the same offset.
- **Main-gear leg door (outside glazing scope, used for sheet L4 / `model/gear.py` LEG_DOOR).**
  - `ngx_dfbox_port` is a near-broadside telephoto of the port gear. The tyre (22 in) sets the scale.
  - It shows the same face as the NGX drawing's side view: a forward edge ~0.5 m ahead of the axle and a pointed
    tip ~0.4 m ahead of it. A concave lower edge rises from the tip to above the hub. The narrow lower part has
    its aft edge near the axle station, then a diagonal step out to the wider upper part.
  - `pro3036_port34_pilatus` (PRO, 3/4 view) shows the same stepped aft edge and concave lower edge.
  - In `ngx_dfbox_port` the door sits ~0.1 m lower relative to the wheel than in the drawing, and on the PRO its
    lower edge also comes close to the hub. This is consistent with the trailing link compressed under load
    (taxiing). The model keeps the drawing's static pose.

## Blender check

Blender 5.0.1 works (`/opt/venv-blender/bin/python`, Cycles on CPU, about 15 s per 1600×800 frame at 8–16 spp).

1. I rendered an orthographic starboard view of `out/pc12.glb`, both shaded and as an alpha silhouette
   (`out/tmp/photos/blender/render_side_ortho*.py`).
2. I resampled `ngx_kenia_stbd_pilatus` into the render's frame with the registration above
   (`out/tmp/photos/blender/overlay_kenia.py`, producing `overlay_kenia_stbd*.jpg`).

What the overlay shows:

- The crown, cowling, spinner and nose-gear leg line up within about 0.05–0.1 m.
- The model side window is too low and too far forward at its lower front, its aft end is too square, and its
  surround tab reaches too far forward.
- The starboard cabin windows sit about 0.6 m too far forward.

## Not established by these photos

- The exact plan-view windshield outline (now the sill / roof / pillar planes of `cockpit_glazing`). No true overhead orthographic shot was found; the two top
  views are oblique, and their variant is unknown.
- Absolute WL values better than ±0.1 m.
- The centre-post width beyond "wider than 0.07 m".
- Radome or radar-pod size differences.
- Anything about the PRO's starboard side beyond what s/n 3001 and 3008 show at modest resolution. These are
  consistent with the NGX starboard window.
