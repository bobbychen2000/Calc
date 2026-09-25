# Aircraft models, livery textures and fonts: sources, licences and required notices

Owner: aircraft / liveries workflow (`tools/convert_models.py`, `tools/liveries/**`, `data/models/**`, `data/liveries/**`).
Companion of `docs/ATTRIBUTION.md` (airport data). Facts below were read on 24 Sep 2026 from the pinned source commits
(clones in the gitignored `refs/cache/src/`); the licence checks are those of `docs/research/liveries.md` §4.1
(`tools/models/livery_sources.py`, adversarially verified). Not legal advice; the owner decides.

## Notices to show in the app (About / credits) and in any distribution

> Airline names, logos and liveries are trademarks of their respective owners. They are re-drawn here for a
> non-commercial depiction of real traffic; no endorsement is implied.
>
> Aircraft models: FlightGear aircraft (FGMEMBERS, GPL-2.0 or later) via FlightAirMap-3dmodels (Ysurac); Boeing
> 737-800 from FGMEMBERS/737-800 (GPL-2.0). Livery textures baked by tools/liveries from our own vector drawings on
> these models' textures (GPL-2.0); the Alaska Airlines 737-800 tail uses the FlightGear livery "N563AS" (GPL-2.0).
> Fonts: Montserrat, Kanit, Nunito, Libre Baskerville, Kalam (SIL Open Font License 1.1).

The same text is requested for `js/live/about.js` in `docs/requests/liveries_brand.md` (not this workflow's file).

## 1. Models (`data/models/*.sfom`)

Converted by `tools/convert_models.py`, then given a livery atlas by `tools/liveries/atlas.py` (see
`docs/research/liveries_impl.md`). Every `.sfom` header carries `source` and `license`.

| Key | Source file | FlightGear origin @ commit pinned by FAM | Licence file at that commit |
|---|---|---|---|
| a319, a320, a321 | FAM `a320/glTF2/A319/A320/A321.glb` | FGMEMBERS/A320-family @0b928542 | COPYING (GPL-2.0) |
| a333 | FAM `a333/glTF2/A333.glb` | FGMEMBERS/A330-300 @7d930769 | COPYING (GPL-2.0) |
| a359 | FAM `a350/glTF2/A350.glb` | FGMEMBERS/A350XWB @407f422a | COPYING (GPL-2.0) |
| a388 | FAM `a380/glTF2/A380.glb` | FGMEMBERS/A380-omega @ffb200c2 | COPYING (GPL-2.0) **and** `License/` (CC-BY-NC-3.0 caveat, below) |
| b744 | FAM `b744/glTF2/B747.glb` | FGMEMBERS/747-400 @99e62214 | COPYING (GPL-2.0) |
| b748 | FAM `b748/glTF2/B748.glb` | FGMEMBERS/747-8i @3f7bcacb | LICENSE (GPL-2.0) |
| b752 | FAM `b752/glTF2/B752.glb` | FGMEMBERS/757-200 @363ac0b9 | LICENSE ("GPL v2 or later") |
| b763 | FAM `b767/glTF2/B763.glb` | FGMEMBERS/767 @a31798b2 | COPYING (GPL-2.0) |
| b788 | FAM `b788/glTF2/B788.glb` | FGMEMBERS/787-8 @c0f1f92f | COPYING (GPL-2.0) |
| bcs1, bcs3 | FAM `bcs1/glTF2/BCS1/BCS3.glb` | FGMEMBERS/CSeries @8a8223f3 | COPYING (GPL-2.0) |
| crj2 | FAM `crj2/glTF2/CRJ2.glb` | FGMEMBERS/CRJ-200 @24fc7611 | COPYING.txt (GPL-2.0) |
| crj7, crj9 | FAM `crj9/glTF2/CRJ7/CRJ9.glb` | FGMEMBERS/CRJ700-family @4862db2f | LICENSE (GPL-2.0 or above) |
| e170, e75l, e190 | FAM `e190/glTF2/E170/E75L/E190.glb` | FGMEMBERS/E-jet-family @9a9b6d06 | License.txt (GPL-2.0) |
| md11 | FAM `md11/glTF2/MD11.glb` | FGMEMBERS/MD-11 @c88139fc | LICENSE ("GPL v2 or later") |
| b738 | `737-800.ac` + wing / stabiliser / winglet / nose-gear `.ac` files | FGMEMBERS/737-800 @9126249 | LICENSE (GPL-2.0) |

FAM = https://github.com/Ysurac/FlightAirMap-3dmodels @0906d9b. FlightGear repositories: https://github.com/FGMEMBERS/<name>.

**A380 caveat (unresolved).** A380-omega @ffb200c2 also ships `License/README`, which says that until 31 May 2015 the
work of Toryx, Tapaninen and Muraleedharan (textures included) was shared under CC-BY-NC 3.0; the relicensing to GPL
is documented only for Muraleedharan ("Omega"), second-hand. Our `a388.sfom` textures (`wing.png`, `tail.png`,
`extra.png`, `rr_fan.png`, `F-WWDD`) and the A380 livery atlas derived from them may therefore still be
**non-commercial only**. Fine for this non-commercial depiction; must be resolved before any commercial use.

**E-jet textures** carry a "Made by theomegahangar.yolasite.com" watermark in the source liveries; the repository is
GPL-2.0 (`License.txt`). Our atlases keep only the neutralised panel-line / window detail of those textures.

**GPL obligations.** The `.sfom` files and every texture derived from them are GPL-2.0 derivative works. The
corresponding source is: the pinned repositories above, plus `tools/convert_models.py`, `tools/ac3d.py`,
`tools/liveries/**` (all in this repository). Keep this file, the `.sfom` `license` / `source` header fields and the
About notice with any copy.

## 2. Livery textures (`data/liveries/<BRAND>/<model>[@<type>]-{hi,mid,lo}.webp`)

Baked by `tools/liveries/build.py` (painter `tools/liveries/paint.py`, designs `tools/liveries/liveries.py`,
vector art `tools/liveries/art.py`).

- **Our own drawings.** Colours, swoops, cheatlines, tail art, titles and emblems are drawn by code from control points
  and vector shapes (`liveries.py`, `art.py`); no airline raster logo, photo or profile drawing is copied. Reference
  images (official press photos, livery graphics, profile drawings) were used only to measure positions and colours and
  are not in the repository (gitignored `refs/cache/`). Each brand's references are listed in
  `data/liveries/manifest.json` (`brands.<CODE>.refs`) and in `docs/research/liveries_impl.md` §6.
- **GPL-derived layer.** Each texture multiplies the model's own panel lines, door outlines and window frames, taken
  from the model's source textures (§1), into the paint, so every livery texture is a GPL-2.0 derivative work of the
  model it belongs to.
- **One FlightGear livery used directly:** the Alaska Airlines tail on the 737-800 (`ASA/b738*.webp`) is sampled from
  `Models/Liveries-800/N563AS.png` of FGMEMBERS/737-800 @9126249 (GPL-2.0; added in commit eb35897, 13 Mar 2016,
  "New liveries from forum", packed by legoboyvdlp, committed by Michael Soitanen). It is the 2016 Alaska livery (current)
  and fits the model's UV layout. On all other Alaska / Horizon / SkyWest-for-Alaska models the tail portrait is our own
  simplified drawing.
- **Trademarks.** GPL and OFL cover copyright only. Airline names, logos and tail art remain trademarks of their owners;
  they are depicted for a non-commercial visualisation of real traffic (owner decision, 24 Sep 2026), with the notice
  above and without implying endorsement.

## 3. Fonts (used at bake time only; not shipped)

Fetched from the Google Fonts CSS API into the gitignored `refs/cache/fonts/` by `tools/liveries/fonts.py`. All SIL Open
Font License 1.1. Only rasterised letter shapes end up in the textures; the font files are not distributed.

| Family (weights) | Used for | Licence |
|---|---|---|
| Montserrat (500, 600, 700, 700i, 800, 800i) | most titles (geometric sans substitutes for the airlines' proprietary faces) | OFL 1.1 |
| Kanit (700i) | Alaska title (italic) | OFL 1.1 |
| Nunito (900) | rounded lower-case titles (JetBlue, Breeze, French bee, Flair) | OFL 1.1 |
| Libre Baskerville (700) | serif titles (Cathay Pacific, British Airways, Lufthansa, Emirates, Starlux, Qatar) | OFL 1.1 |
| Kalam (700) | handwritten 'virgin' tail script | OFL 1.1 |

The real airline wordmarks are proprietary typefaces or custom lettering; ours are look-alike substitutes, listed per
brand in `docs/research/liveries_impl.md` §6.
