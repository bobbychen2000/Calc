# Room area: decisions on the former open questions

The user asked for judgement calls rather than questions. Rule applied: real in-flight photos win.

1. **Boarding set-up:** added. A folded duvet on a white mattress pad in clear plastic lies under the white and blue pillows (`roomBundle`, from tpg_31 and tpg_42).
2. **Bed-mode duvet:** open over the bed from below the pillows to the foot, as in the in-use photo fb_a96b7a65.
3. **Rear-facing seat width:** kept at 0.84 m. tpg_31 and tpg_42 measure it independently, and both w4 raters confirmed it. The entry gap stays as modelled; no plan view was found.
4. **Armrest ledge finish:** the darker brushed grey (#8f959c) of the in-flight photos, not the bright silver of ANA's studio shot c_27313.
5. **Seat-number plaques:** dark glass with blue-lit numbers (c_27313 and the in-flight ff_…17e-and-17f photo).

## Wave 2
6. **Sofa hue (w5a).** ANA's official photos (c_27313 / 27315) show a violet-grey sofa with strong contrast; daylight trip
   reports (tt_seat-1, tpg_31 / 42) show a neutral to warm grey. The model now follows the real in-flight photos (neutral
   charcoal-taupe #5e5c62, darker than the shell). Say if you would rather match ANA's official look.
7. **Closed doors (w5).** `roomPart(part, {doors: 1})` closes the sliding door (ash aisle face in a charcoal frame, top
   level with the aisle-end cap) and raises the pop-up privacy panel ~0.40 m out of the armrest ledge slot. The raised
   panel height and finish are estimated; no photo of it raised was found.

## Wave 3
8. **Boarding bundle restored (w7).** As in decision 1, from tpg_31 / tpg_42 / omaat_room_15: the blue duvet lies on top of
   the white pad, both in plastic, at the cushion front, with the blue pillow resting on it and the white pillow behind. The
   w6 raters asked for the white pad on top; the real photos show the blue on top, so that advice was not followed.
9. **Bundle on the E (forward-facing) seats (w7b question).** Every bundle photo found shows an O bench. ANA sets bedding at
   every seat, so E carries the same bundle [A]. Say if E seats should show pillows only.
10. **Blue pillow tone (w7a question).** The photos disagree: tpg_42 shows pillow/fabric 0.66 and omaat_room_15 shows 1.07.
    The model uses ~0.85 (pillowBlue #4c5594) in both the seat and bed modes.
11. **Monitor wall (w7a).** The frame now runs up level with the cabinet top (tpg_53). The sill stays at the same height,
    so the lighting strip under it (12_scene.js, y 0.642) still lines up.
12. **Spine position on the aisle cap (w10b/w11a/b).** In c_27313 the monument spine meets the aisle-end cap at its centre,
    with a plaque at each end. In the model the cap runs from the O seat's door edge to the monument end, and the spine
    (the O/E split of the monument) meets it 80 % along. Centring it means making the O housing deeper, which shortens O's
    footwell. It is left as is, with the plaques moved to the cap ends. Say if the deeper housing is wanted.
13. **Slipper colour (w8a).** tpg_66 / 67 show light grey slippers and omaat_room_15 a navy pouch. The model keeps navy,
    after the most recent photo.

## Wave 3b (w12)
14. **Pillow pattern (w12).** The KN Aviation 2021 close-up (kn_17) shows the blue pillow as a tone-on-tone check of
    ~1.4 cm squares set on the diagonal; the comforter carries the same jacquard (tpg_81 / 82). Both now use one drawn
    check tile (`tex_j_pillow.png`, period 1.9 cm measured on tpg_46). Note: tpg_72, cited in earlier ratings as the quilted
    comforter, is a photo of the pyjamas; the real bed photos are tpg_79 / 81-83 (new TPG numbering).
15. **Bed-mode comforter (w12a question).** lalf_3 shows it folded back across the full width; tpg_81 shows it loose over
    the pad into the footwell. The model keeps the loose comforter (decision 2). Say if the folded look is wanted.
16. **Plaque numerals (w12a/b question).** c_27315 and kn_36 (day) read white; tlfl_9211 (2024, night) and ff_17e read
    blue-lit. Decision 5 (blue-lit) stays.
17. **Slippers (w12b / w13b).** kn_17 (2021) and tpg_76 (2020) show white slippers in clear film (with a pink amenity
    kit); only omaat_room_15 shows a navy pouch. Two of three real photos, including the latest, win: the slipper pack is
    now white in film (supersedes decision 13).
18. **O bed length (w14a/b, w15a/b).** Both raters estimate the O bed's full-width part at ~0.9 m in tpg_81 against 0.66 m
    in the model (head to the side-table corner). The table position comes from the photo-measured monument layout; a
    Safran / ANA seat-plan dimension would settle it. Left as is.
19. **Real-GPU check (w15).** Please confirm on a real GPU that the ash grain no longer smears at grazing angles (q07) and
    the aisle doors do not alias (q06); the headless renderer cannot show anisotropic filtering.

## Wave 3c (w16)
20. **Belt view (w16b).** No QA or studio view shows the belt and buckle at boarding (pillows and bundle cover it), so the
    webbing / chrome changes cannot be rated. Should a belt close-up be added to the QA views? Both raters' w16 notes on
    the webbing differ: c_27316 (official) shows a teal belt, kn_17 near-black slate; the near-black webbing stays.
21. **Questions 18 (O-bed length) and 19 (real-GPU anisotropic check) remain open.**
