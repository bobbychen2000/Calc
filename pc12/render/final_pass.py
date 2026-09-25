"""
render.final_pass -- high-resolution final renders of render/beauty.py presets, one after another.

    python3 render/final_pass.py [--presets hero,apron_stbd34,...|all] [--glb out/pc12.glb]
            [--out out/renders/final] [--size 3840x2400] [--samples-scale 2] [--min-samples 48]
            [--samples N] [--threshold 0.02] [--adaptive-min 32] [--force] [--dry-run]
            [--set KEY=VALUE ...] [--no-lookdev] [--compare] [--verbose]
    (from pc12/; any python3 -- every preset renders in its own /opt/venv-blender process, override
    with $BLENDER_PYTHON)

For each preset (default: all of beauty.PRESETS, hero first) a worker process imports render/beauty.py
(render/hooks.py; nothing is copied), applies render/lookdev.py if it exists (contract in hooks.py) and
calls beauty.render_preset() at the final size and quality, so a final is exactly the look-dev still, only
bigger and cleaner:
  * --size is beauty's bounding box (3840x2400 default: photo-matched presets keep their photo's aspect,
    e.g. 3200x2400 for a 4:3 photo, 3552x2400 for 'top');
  * samples = max(--min-samples, --samples-scale x the preset's own samples) unless --samples is given;
    adaptive noise threshold --threshold (beauty default 0.03-0.04) with at least --adaptive-min samples
    per pixel; OIDN with the ACCURATE prefilter (cleaner albedo / normal guides at 4K);
  * Cycles auto-tiling stays on (2048 px tiles), which bounds the film memory at 4K;
  * the Cycles light tree is switched off while lights are linked (hooks.light_tree_policy: Cycles 5.0.1's
    light tree + light linking is biased, +20 % on the hero cyclorama, with floor fireflies).
beauty.configure_render and beauty.Scene.camera are wrapped IN THE WORKER PROCESS ONLY (monkey patch, no
edit to beauty.py): the first adds the quality settings (and runs the lookdev hook when render_preset does
not already call lookdev.apply itself -- hooks.beauty_applies_lookdev), the second hands the hook the
preset's beauty.Cam.

Outputs in --out (default out/renders/final/): <preset>.png (8-bit, graded by beauty.finish_png),
<preset>.json (beauty's sidecar + a 'final_pass' block) and manifest.json, rewritten after every preset:
settings, per-preset size / samples / estimate / render and wall time / CPU seconds / peak RSS / PNG bytes.  A preset whose PNG exists with the same
settings (GLB mtime, size, samples, threshold, --set, beauty / lookdev hashes) is skipped unless --force,
so an interrupted pass resumes.  --dry-run prints the plan with upper-bound times on idle cores scaled
(pixels x samples) from the regular beauty sidecars out/renders/<preset>.json (--timings-from DIR) or the
measured K_CPU.

Measured 2026-09-25 (out/pc12_snapshot.glb, lookdev materials, 4 CPUs shared, load ~8): hero at 3840x2400,
16 spp -> 688 cpu-s, 8.3 min wall, peak RSS 3.6 GB, 3.6 MB PNG = 4.7 cpu-s per Mpx per sample (the
lead's 1600x1000 hero sidecar gives 4.6).  Default quality (64 spp, thr 0.02) -> <= 12 min per 4K hero
frame on idle cores (~30 min at that load); all 8 presets <= ~78 min on idle cores (dry run scaled from
the Calc-s2 sidecars: hero 12.0, hangar 13.0, apron 7.6, air 2.9, nose 13.0, wing 11.7, top 8.6,
side 9.4 min).

--compare also writes the photo | render sheets (refs/cache/overlays/vqa/, git-ignored) at final size.
Note: 'top' paints its runway from a generated texture at 16 px/m (beauty.runway_texture), which is
softer than the 4K pixel footprint on the ground (~0.8 cm/px); raise px_per_m there for a 4K 'top'.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from render import hooks  # noqa: E402

B = hooks.import_beauty()
OUT_DIR = ROOT / "out" / "renders" / "final"
ORDER = ("hero", "hangar_port34", "apron_stbd34", "air_below_left", "nose_port_closeup", "wing_from_cabin", "top",
         "side_port_ortho")
DEFAULTS = dict(size="3840x2400", samples_scale=2.0, min_samples=48, threshold=0.02, adaptive_min=32)


def _sha(path, n=12):
    try:
        return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:n]
    except Exception:
        return None


def plan_samples(name, a):
    if a.samples:
        return int(a.samples)
    base = B.PRESETS[name].get("samples", 48)
    return int(max(a.min_samples, round(base * a.samples_scale)))


def preset_size(name, box):
    spec = B.PRESETS[name]["camera"]
    s = min(box[0] / spec["W"], box[1] / spec["H"])
    return int(round(spec["W"] * s)), int(round(spec["H"] * s))


def signature(name, a, glb, box):
    return dict(glb=str(glb), glb_mtime=Path(glb).stat().st_mtime, box=list(box), size=list(preset_size(name, box)),
                samples=plan_samples(name, a), threshold=a.threshold, adaptive_min=a.adaptive_min, set=a.set,
                beauty=_sha(HERE / "beauty.py"),
                lookdev=None if (a.no_lookdev or not hooks.LOOKDEV.exists()) else _sha(hooks.LOOKDEV))


K_CPU = 4.7        # cpu-s per megapixel-sample: hero at 3840x2400 x 16 spp, 2026-09-25 (688 cpu-s incl. setup)


def estimate(name, a, box, ref_dir=None):
    """Upper-bound render time of a preset at the final size / samples on idle cores (cpu-s / (0.95 x
    cores); adaptive sampling usually stops earlier), from the regular beauty sidecar
    out/renders/<name>.json (its render_cpu_s, or render_s x cores) or else K_CPU.  -> (seconds, source)."""
    W, H = preset_size(name, box)
    ncpu = os.cpu_count() or 4
    k, src = K_CPU, "K_CPU model"
    try:
        d = json.loads((Path(ref_dir or B.OUT_DIR) / f"{name}.json").read_text())
        W0, H0 = d["size"]
        t = d["timings"]
        cpu = t.get("render_cpu_s") or t["render_s"] * ncpu * 0.95
        k = cpu / (W0 * H0 / 1e6) / max(d["samples"], 1)
        src = f"{Path(ref_dir or B.OUT_DIR).name}/{name}.json, {k:.1f} cpu-s/Mpx/spp"
    except Exception:
        pass
    return k * (W * H / 1e6) * plan_samples(name, a) / (0.95 * ncpu), src


# =============================================================================================
# worker (inside Blender's python)
# =============================================================================================
def worker(a):
    name = a.worker
    lookdev = hooks.load_lookdev(not a.no_lookdev)
    hooks.apply_sets(B.PRESETS, [name], a.set)
    pre = B.PRESETS[name]
    pre["noise_threshold"] = a.threshold
    box = tuple(int(v) for v in a.size.lower().split("x"))
    samples = plan_samples(name, a)
    in_beauty = hooks.beauty_applies_lookdev(B)          # render_preset calls lookdev.apply itself
    extra = dict(quality=dict(samples=samples, noise_threshold=a.threshold, adaptive_min_samples=a.adaptive_min,
                              denoiser="OIDN", prefilter="ACCURATE", box=list(box)),
                 lookdev=hooks.lookdev_status(lookdev, not a.no_lookdev))
    if in_beauty:
        extra["lookdev"]["applied_by"] = "beauty.render_preset"
        if a.no_lookdev:
            extra["lookdev"]["warning"] = "beauty.render_preset applies lookdev itself: --no-lookdev has no effect"

    orig_camera = B.Scene.camera
    orig_configure = B.configure_render

    def camera(self, cam):
        self._final_cam = cam
        return orig_camera(self, cam)

    def configure_render(S, pre_, samples_, out_png):
        orig_configure(S, pre_, samples_, out_png)
        c = S.sc.cycles
        c.adaptive_min_samples = min(int(a.adaptive_min), int(samples_))
        try:
            c.denoising_prefilter = "ACCURATE"
        except Exception:
            pass
        try:
            c.use_auto_tile = True
        except Exception:
            pass
        hooks.light_tree_policy(S, pre_, extra)          # off with light linking (Cycles 5.0.1 bias)
        if lookdev is not None and not in_beauty:
            extra["lookdev"] = hooks.apply_lookdev(lookdev, S=S, pre=pre_, name=name, info=extra,
                                                   cam=getattr(S, "_final_cam", None), context="final_pass")

    B.Scene.camera = camera
    B.configure_render = configure_render
    out = Path(a.out)
    t0 = time.time()
    B.render_preset(name, a.glb, out, box, samples, a.compare, quiet=not a.verbose)
    ru = resource.getrusage(resource.RUSAGE_SELF)
    extra.update(worker_wall_s=round(time.time() - t0, 1), cpu_s=round(ru.ru_utime + ru.ru_stime, 1),
                 peak_rss_mb=round(ru.ru_maxrss / 1024.0, 1))
    side = out / f"{name}.json"
    d = json.loads(side.read_text())
    d["final_pass"] = extra
    side.write_text(json.dumps(d, indent=1, default=float))
    return 0


# =============================================================================================
# driver
# =============================================================================================
def _meminfo():
    try:
        m = dict(l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines())
        return {k: round(int(m[k].split()[0]) / 1024 / 1024, 2) for k in ("MemTotal", "MemAvailable")}
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--presets", default="all", help="comma list or 'all' (hero first)")
    ap.add_argument("--glb", default=str(B.GLB))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--size", default=DEFAULTS["size"], help="bounding box WxH (presets keep their aspect)")
    ap.add_argument("--samples-scale", type=float, default=DEFAULTS["samples_scale"])
    ap.add_argument("--min-samples", type=int, default=DEFAULTS["min_samples"])
    ap.add_argument("--samples", type=int, default=None, help="fixed samples for every preset")
    ap.add_argument("--threshold", type=float, default=DEFAULTS["threshold"], help="adaptive noise threshold")
    ap.add_argument("--adaptive-min", type=int, default=DEFAULTS["adaptive_min"], help="adaptive min samples")
    ap.add_argument("--force", action="store_true", help="re-render presets that are already done")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timings-from", default=None, metavar="DIR",
                    help="beauty sidecars to scale the estimates from (default out/renders)")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a preset field (beauty.py --set syntax; applies to every listed preset)")
    ap.add_argument("--no-lookdev", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--worker", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    glb = Path(a.glb)
    if not glb.is_absolute():
        glb = (Path.cwd() / glb) if (Path.cwd() / glb).exists() else ROOT / a.glb
    a.glb = str(glb.resolve())
    a.out = str(Path(a.out).resolve())
    if a.worker:
        if not hooks.have_bpy():
            raise SystemExit("--worker must run in Blender's python")
        return worker(a)

    names = [n for n in ORDER if n in B.PRESETS] + [n for n in B.PRESETS if n not in ORDER] \
        if a.presets == "all" else [n.strip() for n in a.presets.split(",") if n.strip()]
    for n in names:
        if n not in B.PRESETS:
            raise SystemExit(f"unknown preset {n!r}; have {', '.join(B.PRESETS)}")
    box = tuple(int(v) for v in a.size.lower().split("x"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    man_path = out / "manifest.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else {}
    man.setdefault("presets", {})
    man.update(tool="render/final_pass.py", glb=a.glb, glb_mtime=glb.stat().st_mtime, box=list(box),
               quality=dict(samples_scale=a.samples_scale, min_samples=a.min_samples, samples=a.samples,
                            threshold=a.threshold, adaptive_min=a.adaptive_min, set=a.set),
               lookdev=None if a.no_lookdev else (str(hooks.LOOKDEV.relative_to(ROOT)) if hooks.LOOKDEV.exists() else "absent"),
               host=dict(cpus=os.cpu_count(), **_meminfo()))

    print(f"[final] {len(names)} preset(s), box {box[0]}x{box[1]} -> {out}", flush=True)
    todo = []
    for n in names:
        W, H = preset_size(n, box)
        sig = signature(n, a, glb, box)
        png = out / f"{n}.png"
        done = png.exists() and man["presets"].get(n, {}).get("signature") == sig and not a.force
        est, src = estimate(n, a, box, a.timings_from)
        print(f"  {n:18s} {W}x{H}  {sig['samples']:4d} spp  thr {a.threshold}"
              + f"  <= {est / 60:5.1f} min on idle cores ({src})"
              + ("  [done, skip]" if done else ""), flush=True)
        if not done:
            todo.append((n, sig, est))
    if a.dry_run:
        return 0

    t_all = time.time()
    fwd = ["--glb", a.glb, "--out", a.out, "--size", a.size, "--samples-scale", str(a.samples_scale),
           "--min-samples", str(a.min_samples), "--threshold", str(a.threshold), "--adaptive-min", str(a.adaptive_min)]
    if a.samples:
        fwd += ["--samples", str(a.samples)]
    for kv in a.set:
        fwd += ["--set", kv]
    for flag in ("no_lookdev", "compare", "verbose"):
        if getattr(a, flag):
            fwd.append("--" + flag.replace("_", "-"))
    failed = []
    for n, sig, est in todo:
        for old in (out / f"{n}.png", out / f"{n}.json"):     # never report a stale file as this run's
            if old.exists():
                old.unlink()
        cmd = [B.BLENDER_PY, str(Path(__file__).resolve()), "--worker", n] + fwd
        t = time.time()
        load0 = os.getloadavg()
        p = subprocess.Popen(cmd, cwd=str(ROOT))
        _, status, ru = os.wait4(p.pid, 0)
        wall = time.time() - t
        rc = os.waitstatus_to_exitcode(status)
        png, side = out / f"{n}.png", out / f"{n}.json"
        ent = dict(status="ok" if rc == 0 and png.exists() else f"failed (exit {rc})", signature=sig,
                   estimate_idle_s=round(est, 1), wall_s=round(wall, 1), cpu_s=round(ru.ru_utime + ru.ru_stime, 1),
                   peak_rss_mb=round(ru.ru_maxrss / 1024.0, 1), load_avg_start=[round(v, 2) for v in load0],
                   load_avg_end=[round(v, 2) for v in os.getloadavg()],
                   finished=time.strftime("%Y-%m-%d %H:%M:%S"))
        if rc == 0 and png.exists():
            d = json.loads(side.read_text())
            W, H = d["size"]
            ent.update(png=str(png.relative_to(ROOT)) if png.is_relative_to(ROOT) else str(png), bytes=png.stat().st_size,
                       size=[W, H], megapixels=round(W * H / 1e6, 2), samples=d.get("samples"),
                       timings=d.get("timings"), camera_source=d.get("camera_source"),
                       lookdev=d.get("final_pass", {}).get("lookdev"),
                       light_tree=d.get("final_pass", {}).get("light_tree"),
                       cpu_s_per_megapixel_sample=round(ent["cpu_s"] / (W * H / 1e6) / max(d.get("samples", 1), 1), 3))
        else:
            failed.append(n)
        man["presets"][n] = ent
        man["total_wall_s_this_run"] = round(time.time() - t_all, 1)
        man["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        man_path.write_text(json.dumps(man, indent=1, default=float))
        print(f"[final] {n}: {ent['status']}, wall {wall / 60:.1f} min, {ent['cpu_s'] / 60:.1f} cpu-min, "
              f"peak RSS {ent['peak_rss_mb']:.0f} MB" + (f", {ent['bytes'] / 1e6:.1f} MB PNG" if 'bytes' in ent else ""),
              flush=True)
    print(f"[final] done in {(time.time() - t_all) / 60:.1f} min; manifest {man_path}"
          + (f"; FAILED: {', '.join(failed)}" if failed else ""), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
