"""Writes the adversarial fact-check (tools/buildings/dom_verify.py -> dom_verify.json; docs/research/buildings_domestic.md
section "Verification") into tools/buildings/spec_domestic.json.

Each checked item gets `verification` = {verdict, evidence, date}; a refuted or corrected value keeps the old one in
`corrected` = {field, previous, reason}. Idempotent: an item that already carries `corrected` is not overwritten again,
so re-running keeps the original previous values. Called by `dom_verify.py --apply` and at the end of
build_spec_domestic.py (which regenerates the spec without these records).
"""
import json, math

DATE = '2026-11-04'
FT = 0.3048
VSRC = 'refs/cache/buildings/domestic/src/verify/'


def apply(path, V):
    spec = json.load(open(path))
    I = {it['id']: it for it in spec['items']}
    O = V['sun_2020']['options']
    H = V['heights_at_sunpath_s20']
    B, BS = V['ba_b'], V['ba_b_section']
    tw = V['tower_shadow_2020']

    def verify(iid, verdict, evidence, **upd):
        it = I.get(iid)
        if it is None:
            return None
        it['verification'] = dict(verdict=verdict, evidence=evidence, date=DATE)
        reason = upd.pop('_reason', verdict)
        if upd:
            prev = {k: it.get(k) for k in upd}
            if 'corrected' not in it:
                it['corrected'] = dict(field=', '.join(upd), previous=prev, reason=reason)
            it.update(upd)
        return it

    def hrange(rid):
        h = H[rid]; return [min(h.values()), max(h.values())]

    s20_txt = ('|s20| (2020 shadow per m of height) is DISPUTED: the sun path at the research\'s own ATCT azimuth 87.4 deg gives '
               '%.3f, not 1.19 (1.19 needs 86.7 deg); the re-measured shadow centre line gives %.2f-%.2f deg -> %.3f-%.3f; '
               'the FAA DOF control 06-035331 (34 +- 3 ft) is best fitted by ~1.27 and only bounds |s20| to 1.17-1.40; only '
               'the BA-A pole-lean check (extrapolated ITB pole model) favours 1.19. Adopted: 1.25, range 1.19-1.31 '
               '(heights x 0.95, range x 0.90-1.00).' % (V['sun_2020']['research_azimuth']['s20_abs'],
               tw['alt_range_-693'], tw['heading_deg'], V['sun_2020']['remeasured_azimuth_alt_range']['s20_abs'],
               V['sun_2020']['remeasured_azimuth']['s20_abs']))

    # ------------------------------------------------------------------------------------------------- method
    it = I['sun.2020']
    verify('sun.2020', 'DISPUTED (precision refuted; value corrected)', s20_txt,
           value=dict(shadow_azimuth_deg=O['central']['shadow_az'], shadow_len_per_m=O['central']['s20_abs'],
                      shadow_len_range=[O['calibrated']['s20_abs'], O['sunpath']['s20_abs']],
                      sun_elevation_deg=round(math.degrees(math.atan(1 / O['central']['s20_abs'])), 1)),
           _reason='independent sun-path / tower-shadow check (doc Verification V.2)')
    verify('sun.2024', 'CONFIRMED', 'sun path 2024-05-20 at azimuth 186.5 deg: el 72.50 deg, 0.315 m/m (dom_sun.py re-run); '
           'noon maximum 72.6 deg')
    verify('control.ba_a', 'PLAUSIBLE (value scale-dependent)',
           'reproduced 18.74 m at |s20| 1.19; %.2f m at 1.25, %.2f at 1.31. The ITB research measures 17.0 +- 2.5 (low) '
           'on the same roof. Its agreement with the ITB pole lean (k24.x 0.418) is the only evidence for 1.19; that lean '
           'is extrapolated from poles 120-400 m west and rests on DOF base positions (1A: +-20 ft)' % (H['ba_a_body']['central'], H['ba_a_body']['sunpath']),
           value=H['ba_a_body']['central'], range=hrange('ba_a_body'), _reason='|s20| corrected (V.2)')
    verify('control.ba_f_dof', 'DISPUTED as a calibration',
           'DOF 06-035331 lies inside the BA-F outline at the NE arm tip (on the building). 11.03 m vs 10.36 m is a 6.5 %% '
           'misfit at |s20| 1.19; the DOF +-3 ft allows |s20| 1.17-1.40, best 1.27. At the adopted 1.25: %.2f m (DOF 10.36).' % H['ba_f_ne_arm']['central'])
    verify('outline.level', 'CONFIRMED', 'SFO Museum record 1947304261 (Boarding Area B, raw GeoJSON re-fetched): '
           'sfo:level 2, wfnd:level 2 (%ssfom_bab.geojson)' % VSRC)

    # ----------------------------------------------------------------------------------------------- T1 Center
    for iid in ('t1c.skylight_truss_h', 't1c.skylight_reflectors'):
        it = I[iid]
        if 'corrected' not in it:
            it['corrected'] = dict(field='value, group, status', previous=dict(value=it['value'], group=it['group'], status=it['status']),
                                   reason='the SFO Museum page places the work in the Dianne Feinstein INTERNATIONAL Terminal, '
                                          'Main Hall - Level 3 (2000), not in Harvey Milk Terminal 1')
        it['value'] = None; it['status'] = 'refuted'; it['confidence'] = 'n/a'
        it['applies_to'] = 'international_terminal (ITB) main hall - pass to the ITB research'
        it['verification'] = dict(verdict='REFUTED (wrong building)', date=DATE, evidence=(
            'Re-fetched %ssfom_reflectors.html: breadcrumb "Four Sculptural Light Reflectors - Dianne Feinstein '
            'International Terminal - Main Hall - Level 3 - Pre-Security", dated 2000 (the ITB opened in 2000); "inserted '
            'within the truss structure of the skylights, 70 feet above the floor"; "the four 180 x 30-foot sculptures". '
            '"Harvey Milk Terminal 1" appears only in the page\'s terminal navigation list. The same page\'s dimension field '
            'reads "L160 in. x W25 in. each" (conflicts with 180 x 30 ft).' % VSRC))
    verify('t1c.skylights_count', 'CORRECTED (conflict dissolved)',
           'The 4 reflectors are in the ITB (above), so the only T1 Center source is Airport Improvement 2020 (Gensler, '
           'T1 Center section): "Three large skylights provide daylighting in the tremendous space". NAIP 2024 shows three '
           '~9 x 11 m glazed openings (t1c.roof_pv) - consistent.',
           value=dict(airport_improvement_2020=3), status='verified', confidence='medium',
           _reason='the SFO Museum count belongs to the ITB')
    it = I['t1c.h_roof']
    it['note'] = ('not measured and NOT published: curved faces, the landside faces over roadways / garage. (The earlier lower '
                  'bound "Level 3 floor + 70 ft" was refuted: that 70 ft is the ITB main hall.)')
    it['verification'] = dict(verdict='STILL UNKNOWN', evidence='no T1 Center height in any re-read source', date=DATE)
    it['sources'] = ['naip']
    verify('t1.phases', 'CONFIRMED', 'flysfo 17 Jun 2024 press release re-read (final phase: north lobby, mezzanine '
           'checkpoint, gates B3 and C1, connector); Airport Improvement 2020: first 9 gates + part of T1 Center July 2019, '
           '9 more gates + south lobby May 2020; Arup: "opened in three phases (2019, 2020, and 2021)". The exact day '
           '23 Jul 2019 was not re-read.')
    verify('t1.area', 'CONFIRMED as published (conflict stands)', 'DBIA 619,150 sq ft; Airport Improvement 617,700 sq ft "on '
           '3 levels including MARS stands"; Cupertino Electric adds "500,000-square-foot project" (BA-B).')
    verify('t1.dof_2013', 'CONFIRMED (values); location note added',
           'DOF re-fetched: 06-035351 50 ft lies inside the T1 outline (2013 survey, old South Terminal); 06-035323 17 ft is '
           '60 m outside any outline and 06-035322 24 ft 26.7 m outside BA-C: apron objects, not buildings.')

    # -------------------------------------------------------------------------------------------------- BA-B
    verify('bab.gates', 'CONFIRMED', 'Arup and DBIA: 25 gates; Airport Improvement: "25 (including 4 int\'l swing gates)"')
    verify('bab.levels', 'CONFIRMED', 'Arup: "two levels and a mezzanine"; RDH: "three-story, concrete-framed"; '
           'DBIA: mezzanine with airline clubs and an international corridor')
    verify('bab.structure', 'CONFIRMED', 'Airport Improvement: "100-foot-deep piles"; RDH: concrete frame on a pile foundation')
    verify('bab.glazing', 'CONFIRMED', 'Airport Improvement: View Dynamic Glass 112,000 sq ft; Arup: electrochromic glazing '
           'throughout the concourse level with Low-E glazing at the clerestory level')
    verify('bab.pv', 'CONFIRMED', 'Cupertino Electric: "1.2-MWDC rooftop array consisting of nearly 3,000 PV panels"; Arup / '
           'RDH: 1 MW')
    verify('bab.pv_layout', 'PLAUSIBLE (width corrected)',
           'autocorrelation of the median s-profile over the central field (t -1236..-1180): pitch 9.1 m (2020) / 9.3 m '
           '(2024); dark-row widths 5.7-7.1 m (threshold at mid level), wider than "~5.5 m". The PV field sits on the RAISED '
           'central roof (parallax 3.40 m); single PV rows also lie on the lower side bands (parallax 2.25 m).')
    sec = BS['central']
    hO, hM = sec['h_low'], sec['h_central']
    rngO = [BS['sunpath']['h_low'], BS['calibrated']['h_low']]
    rngM = [BS['sunpath']['h_central'], BS['calibrated']['h_central']]
    evB = ('Local 1-D NCC shifts 2020->2024 in 6 m windows across the roof (dom_verify.py): the central field (s -417..-391) '
           'moves %.2f m, the WNW side band (s -433..-425) %.2f m, the ESE outer lip %.2f m (2020 %.2f -> 2024 %.2f), '
           'all with r > 0.95; 2022->2024 is ~0 everywhere. Different shifts = different heights (h_low / h_central = %.2f, '
           'independent of the sun and the leans). In 2020 the ESE strip s -388..-382 that the research read as a dark '
           'roof strip "at the same height" is SHADOW of the raised central roof on the lower band (it is white roof with '
           'one thin PV row in 2024); its length %.1f m confirms the step. The research paired the outer-edge bands '
           '(band20 %.2f, band24 %.2f) with the CENTRAL field shift p = %.2f; with the outer edges\' own shift p = %.2f: '
           'h_low = (band20 + band24 - p) / den = %.2f m at |s20| 1.25 (%.2f-%.2f over 1.19-1.31); central roof = '
           'h_low x %.2f / %.2f = %.2f, or h_low + step shadow / (s20 - k20).n = %.2f -> %.2f m.' % (
               B['p_central'], B['p_low_wnw_band'], B['p_low_ese_lip'], B['ese_lip_2020'], B['ese_lip_2024'],
               B['ratio_low_central'], B['step_shadow_2020'], B['band20'], B['band24'], B['p_research'], B['p_low'],
               hO, rngO[0], rngO[1], B['p_central'], B['p_low'], sec['h_central_parallax'], sec['h_central_step_shadow'], hM))
    verify('bab.h_roof', 'CORRECTED (derivation refuted; the value ~holds for the OUTER edges by compensating errors)', evB,
           value=hO, value_ft=round(hO / FT, 1), sd_m=0.7, range=rngO, name='Outer (lower) roof edges, both sides, south half (t -1238..-1176)',
           _reason='stepped section: wrong parallax paired with the outer-edge bands; |s20| corrected (doc Verification V.3/V.4)')
    if 'bab.h_roof_central' not in I:
        new = dict(id='bab.h_roof_central', group='boarding_area_b', name='Raised central roof (PV field) above apron, south half',
                   value=hM, unit='m', tag='obs', sources=['naip'], source_urls=[], confidence='low', status='verified',
                   value_ft=round(hM / FT, 1), sd_m=1.0, range=rngM,
                   method='parallax ratio (central field 3.40 m vs outer edges 2.28 m) times the outer-edge height; '
                          'cross-checked by the 2020 shadow of the step on the lower ESE band',
                   note='the step (~%.0f m) is the "clerestory" of Arup ("Low-E glazing at the clerestory level"). Plan '
                        '(lean-corrected, approximate): lower band ~7.5 m wide on the ESE side, ~14 m on the WNW side, raised '
                        'part ~33 m wide' % (hM - hO),
                   verification=dict(verdict='NEW (from the verification)', evidence=evB, date=DATE))
        spec['items'].insert(spec['items'].index(I['bab.h_roof']) + 1, new); I[new['id']] = new
    te = I['bab.roof_edges']
    if 'corrected' not in te:
        k20n, k24n = sec['k20_n'], sec['k24_n']
        un = 4.49 - k20n * hO; um = 0.55 + k24n * hO
        te['corrected'] = dict(field='value.n_offset_from_line, value.m_offset_from_line, note',
                               previous=dict(n_offset_from_line=te['value'].get('n_offset_from_line'),
                                             m_offset_from_line=te['value'].get('m_offset_from_line'), note=te.get('note')),
                               reason='lean-free edges recomputed with the outer-edge height and leans of V.4')
        te['value']['n_offset_from_line'] = round(un, 2); te['value']['m_offset_from_line'] = round(um, 2)
        # research: the n_face line lies on the outline (true edge 3.31 out = 3.32 outside the outline); the outline is
        # 5.08 + 1.66 = 6.74 m outward of the m_face line
        te['note'] = ('n_line / m_line endpoints are the research values; the corrected offsets from the research face lines '
                      'are n_offset_from_line / m_offset_from_line: ESE true outer edge ~%.1f m outside the level-2 outline '
                      '(was 3.3), WNW ~%.1f m inside it (was 1.6); outer-roof width ~%.1f m (outline 53.7)' % (
                          un + 0.01, 6.74 - um, 55.41 - (3.31 - un) - (5.08 - um)))
        te['verification'] = dict(verdict='CORRECTED', evidence='outline offsets re-measured (shapely, SFO Museum outline): the '
                                  'research lines lie 3.32 m (ESE) and 1.66 m (WNW) from the outline as stated; the overhang '
                                  'shrinks with the corrected leans', date=DATE)
    verify('bab.clerestory', 'CONFIRMED and measured', 'Arup re-read ("Low-E high performance glazing at the clerestory '
               'level"); the NAIP parallax and the 2020 step shadow show the raised central roof ~%.0f m above the outer '
               'roof (bab.h_roof_central)' % (hM - hO))

    # -------------------------------------------------------------------------------------------- BA-C / D / E / F
    verify('bac.h_roof', 'PLAUSIBLE (low; scale-dependent)', 'reproduced 7.54 m at |s20| 1.19; %.2f at 1.25, %.2f at 1.31; the '
           'assumed k24.x 0.40 is not independently checked' % (H['ba_c_east']['central'], H['ba_c_east']['sunpath']),
           value=H['ba_c_east']['central'], range=hrange('ba_c_east'), _reason='|s20| corrected (V.2)')
    d = V['dof']
    verify('bad.dof', 'REFUTED as BA-D roof heights',
           'the three points lie %.1f, %.1f and %.1f m OUTSIDE the BA-D outline (06-035330, 321, 320); DOF accuracy 1A is '
           '+-20 ft (6 m) horizontally, so none is on the pier. 24-25 ft matches apron structures (e.g. jet-bridge '
           'rotundas), not identified. They cannot check bad.h_roof.' % (d['06-035330']['distance_outside_m'],
                                                                       d['06-035321']['distance_outside_m'], d['06-035320']['distance_outside_m']),
           status='refuted', _reason='location test against the SFO Museum outline (V.5)')
    verify('bad.h_roof', 'PLAUSIBLE (low; no control)', 'reproduced 8.92 m at |s20| 1.19; %.2f at 1.25, %.2f at 1.31. Its '
           'two faces are 118 m apart (true width) and the local parallax across the head varies 0.5-7 m: the head is not '
           'one level. The DOF "check" does not apply (bad.dof).' % (H['ba_d_head']['central'], H['ba_d_head']['sunpath']),
           value=H['ba_d_head']['central'], range=hrange('ba_d_head'), _reason='|s20| corrected (V.2)')
    verify('bad.gates', 'CONFIRMED', 'Gensler T2 page: "accommodates 14 gates"')
    e = V['ba_e']
    verify('bae.h_roof', 'PLAUSIBLE (scale-dependent)',
           'the roof is ONE level across its width (local parallax %.2f m median, %.2f-%.2f over s -718..-694, r > 0.95), '
           'so the fascia method holds; the fascia lip pick allows band20 10.6-11.3 m (-0.6 m). Reproduced 13.51 m at '
           '|s20| 1.19; %.2f at 1.25, %.2f at 1.31.' % (e['p_roof_median'], e['p_roof_range'][0], e['p_roof_range'][1],
                                                      H['ba_e_north']['central'], H['ba_e_north']['sunpath']),
           value=H['ba_e_north']['central'], value_ft=round(H['ba_e_north']['central'] / FT, 1), range=hrange('ba_e_north'),
           _reason='|s20| corrected (V.2)')
    verify('bae.roof', 'CONFIRMED', 'IDA entry re-read: "With tapered edges overhanging clerestory glazing, the roof is '
           'structured with lightweight, long-span trusses ... remove the existing middle two rows of structural columns"')
    verify('bae.renovation', 'CONFIRMED', 'Hensel Phelps news re-read: Saturday 25 Jan 2014, 10 United gates, $138 M, '
           'Hensel Phelps / Gensler / KPA')
    verify('bae.area', 'CONFIRMED as published', 'Hensel Phelps: 68,800 sq ft BA-E (+150,000 sq ft eastern concourse)')
    verify('baf.h_roof_ne_arm', 'PLAUSIBLE (scale-dependent)', 'reproduced 11.03 m at |s20| 1.19; %.2f at 1.25 (DOF 06-035331: '
           '10.36), %.2f at 1.31. Local parallax at the ESE edge 1.75-1.85 m vs the research\'s 1.98.' % (
               H['ba_f_ne_arm']['central'], H['ba_f_ne_arm']['sunpath']),
           value=H['ba_f_ne_arm']['central'], value_ft=round(H['ba_f_ne_arm']['central'] / FT, 1), range=hrange('ba_f_ne_arm'),
           _reason='|s20| corrected (V.2)')
    verify('baf.dof', 'CONFIRMED (331); 332 is not BA-F',
           '06-035331 (34 ft, 1A, 2013289) lies inside the BA-F outline at the NE arm tip; 06-035332 (16 ft) lies %.1f m '
           'outside the T3 outline, beyond the pier tip on the apron (a jet bridge / apron object, not a "lower end '
           'structure")' % d['06-035332']['distance_outside_m'])

    # --------------------------------------------------------------------------------------------- T2 / T3
    verify('t2.area_levels', 'CONFIRMED', 'Airport Improvement 2011 re-read: "640,000-square-foot, two-level structure"')
    verify('t2.history', 'CONFIRMED (Wikipedia-level detail)', 'Airport Improvement: $383 M renovation; Wikipedia: opened '
           'Aug 27 1954, reopened 14 Apr 2011; the International-Terminal rebuild is dated 1983 in one Wikipedia passage and '
           '1984 in another (secondary)')
    verify('t2.daylight', 'CONFIRMED', 'Airport Improvement 2011: "skylights and clerestories"; "Large, floating angular planes '
           'in the roof"')
    verify('t3.levels_datum', 'CONFIRMED', 'CDR CD Phase 3 re-read (pdftotext): T3 L1 11\'-0", T3W L1 10\'-3", L2 27\'-0", '
           'L2M 42\'-6", L3 FIS 45\'-0", "T3 R2 TOP OF ROOF @ HIGH PT." 58\'-6", "T3 R3 TOP OF ROOF @ HIGH PT." 81\'-0", '
           '"T3W TOP OF PARAPET" 66\'-0". No datum is printed (still open).')
    verify('t3.heights_above_L1', 'CONFIRMED (arithmetic)', '58\'-6" - 11\'-0" = 47.5 ft = 14.48 m; 81\'-0" - 11\'-0" = 70.0 ft = '
           '21.34 m. Relative to L1, not to the apron (datum unknown).')
    verify('t3w.wall_field', 'CONFIRMED with a wording fix', 'the field section prints 10\'-00", 18\'-00", 16\'-00", 56\'-00", '
           '10\'-00", 2\'-00" and 0\'-42" (42" parapet): the 22\'-0" above the international level is the sum 10 + 10 + 2 ft, '
           'not a printed dimension')
    verify('t3w.wall_gatehouse', 'CONFIRMED', 'prints 10\'-00", 18\'-00", 16\'-09", 59\'-07" and an 8\'-00" penthouse '
           'enclosure')
    verify('t3w.scope', 'CONFIRMED', 'flysfo 20 Aug 2024 re-read: $2.6 B, 650,000 sq ft renovated, +200,000 sq ft, a new '
           'six-story building (opening early 2028); expanded section fall 2027; east check-in lobby early 2029. '
           '"Courtyard 4" is the CDR name, not in the press release.')
    verify('garage_antenna', 'PLAUSIBLE (not re-read)', 'DOF 06-039216 re-read: BLDG, 130 ft AGL, accuracy 4D (+-250 ft '
           'horizontal / +-50 ft vertical), study 2012AWP07455OE; its DOF position falls INSIDE the T3 outline, which 4D '
           'allows. The OE/AAA case page was not re-fetched (endpoint 404).')

    # ------------------------------------------------------------------------------------------------- photos
    for p in spec.get('photos', []):
        if p['file'].endswith(('p17.jpg', 'p18.jpg', 'p19.jpg', 'p20.jpg')) and 'corrected' not in p:
            p['corrected'] = dict(field='author', previous=p['author'], reason='HTML residue of the Commons creator template')
            p['author'] = 'Benoît Prieur'
        p['verification'] = 'licence and author re-checked against the Commons API on %s (%scommons_verify.json)' % (DATE, VSRC)

    # ---------------------------------------------------------------------------------- lists and status lines
    spec['verified'] = dict(date=DATE, doc='docs/research/buildings_domestic.md#verification', tool='tools/buildings/dom_verify.py',
                            numbers='tools/buildings/dom_verify.json')
    spec['current_model_deviations'][0] = ('tools/build_terminal_parts.py: every pier PIER_H = 14.6 m. Measured (verified, |s20| '
                                           '1.25, range -5 %%/+5 %%): BA-B outer edges %.1f with a raised central roof %.1f, '
                                           'BA-E %.1f, BA-F NE arm %.1f (DOF 10.4), BA-D ~%.1f (low), BA-C ~%.1f (low)' % (
                                               hO, hM, H['ba_e_north']['central'], H['ba_f_ne_arm']['central'],
                                               H['ba_d_head']['central'], H['ba_c_east']['central']))
    spec['current_model_deviations'][1] = ('tools/build_terminal_parts.py: HALL_H T1 20.0 / T2 19.0 / T3 21.0 m "approximate". '
                                           'Published T3: roof high points 47.5 ft (14.5 m, R2) and 70 ft (21.3 m, R3) above '
                                           'L1 (datum unknown); T1 and T2: no published or measured height (the "70 ft" '
                                           'skylight trusses are the ITB\'s)')
    oq = spec['open_questions']
    oq[:] = [q for q in oq if not q.startswith(('T1 Center and T2 main-hall', 'BA-B clerestory', 'BA-C and BA-D heights',
                                                'Cross-workflow: the ATCT shadow'))]
    for q in [
        'T1 Center and T2 main-hall roof heights: nothing published (the 70 ft skylight-truss figure belongs to the ITB). A '
        'licensed photo with a scale reference or an SFO section drawing would close it.',
        'NAIP 2020 sun: |s20| is 1.19-1.31 (adopted 1.25). The acquisition time of the 2020 strips (USDA seamline / flight '
        'logs) or a pole of known height with a measurable 2020 shadow would fix the scale of every two-epoch height '
        '(+-5 %). Different strips may also carry different sun times.',
        'BA-B: the stepped section (outer edges ~13 m, raised central roof ~19 m) is measured on the south half only; the '
        'north half, the roof wells and the exact step lines need the same parallax scan.',
        'BA-C and BA-D: low confidence; the DOF points near D are not on the pier (bad.dof).',
        'Cross-workflow (tower): the domestic research\'s tower axis x -733.5 assumed |s20| 1.19; at 1.25-1.31 the same '
        'shadow puts the axis ~4-8 m further west (~-737 to -741), i.e. no conflict with the tower research.',
        'ITB research: the SFO Museum "Four Sculptural Light Reflectors" page gives the ITB main hall: skylight trusses 70 ft '
        'above the Level 3 floor, four 180 x 30 ft reflectors (2000).',
    ]:
        if q not in oq: oq.append(q)
    spec['status'] = spec['status'].split(' Verified')[0] + ' Verified adversarially on %s (doc section "Verification").' % DATE
    json.dump(spec, open(path, 'w'), indent=1, ensure_ascii=False)
    return spec
