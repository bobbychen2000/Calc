"""
render.hooks -- shared glue for the Blender render drivers built on render/beauty.py
(render/turntable.py, render/final_pass.py): import beauty once under both of its names, apply the
optional render/lookdev.py, switch the Cycles light tree off while lights are linked (light_tree_policy:
a Cycles 5.0.1 bias, measured there), and parse beauty-style --set overrides.  Pure python (no bpy at
import), nothing here edits beauty.py.

lookdev contract (render/lookdev.py is optional; it belongs to the look-development work):
  * Importing it may patch render.beauty in place (PRESETS, PAINT_FLAKE, GLASS_TINT, HERO_LIGHTS, Scene
    methods, ...).  beauty is registered as BOTH 'render.beauty' and 'beauty' (the same module object),
    so a patch made through either name is seen by the drivers.
  * If it defines apply(...), apply_lookdev(...) or apply_look(...) (first found), the driver calls it
    once per scene where beauty.render_preset does (right after beauty's Scene.materials(), before the
    pose and the environment); final_pass.py leaves that to render_preset when beauty already calls it
    (beauty_applies_lookdev).  Arguments are bound by PARAMETER NAME:
        S / scene / beauty_scene     -> beauty.Scene (S.bpy, S.sc, S.parts, S.meshes, S.materials() ...)
        pre / preset / spec / cfg    -> the preset dict being rendered (already --set-overridden)
        name / preset_name           -> preset name ('turntable' for the turntable)
        info / meta                  -> the sidecar-JSON dict (the hook may add keys)
        cam / camera                 -> beauty.Cam of the (first) frame
        bpy                          -> the bpy module
        context / mode / driver      -> 'turntable' | 'final_pass'
        target / materials / mats    -> bpy.data.materials
        overrides / lookdev_overrides -> pre.get('lookdev') (per-material overrides, as beauty passes them)
    a **kwargs parameter receives every key above that is not bound otherwise; any other required
    parameter gets S if it is the first one, else the call fails with a clear error.  Its return value
    (if a dict) is stored in info['lookdev']['result'].
  * Errors in lookdev are fatal (a half-applied look is worse than no render); --no-lookdev skips it.
"""
from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LOOKDEV = HERE / "lookdev.py"
LOOKDEV_FUNCS = ("apply", "apply_lookdev", "apply_look")
_ALIAS = {
    "s": "S", "scene": "S", "beauty_scene": "S", "bscene": "S",
    "pre": "pre", "preset": "pre", "spec": "pre", "cfg": "pre", "config": "pre",
    "name": "name", "preset_name": "name",
    "info": "info", "meta": "info",
    "cam": "cam", "camera": "cam",
    "bpy": "bpy",
    "context": "context", "mode": "context", "driver": "context",
    "target": "materials", "materials": "materials", "mats": "materials",
    "overrides": "overrides", "lookdev_overrides": "overrides",
}


def import_beauty():
    """render.beauty, importable as 'beauty' too (one module object)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    B = importlib.import_module("render.beauty")
    sys.modules.setdefault("beauty", B)
    return B


def beauty_applies_lookdev(B):
    """True if beauty.render_preset itself calls lookdev.apply (then a driver that goes through
    render_preset must not apply it a second time)."""
    try:
        return "lookdev" in inspect.getsource(B.render_preset)
    except Exception:
        return False


def light_tree_policy(S, pre, info=None):
    """Cycles 5.0.1: the light tree with LIGHT LINKING is biased and firefly-prone.  Measured on the hero
    cyclorama (overhead + rims linked to the cyclorama, 128 spp, no denoise, aircraft hidden): light tree
    on -> wall 82.3 / floor 56.2 (sRGB means) and ~1100 floor fireflies in a 480x270 frame; light tree off
    -> 67.7 / 49.1, which equals the render WITHOUT linking (tree on or off) = the correct answer; the
    fireflies are the 'glitter' on the glossy floor.  So: pre['light_tree'] None (default) switches the tree
    off when any light carries a receiver / blocker collection (with a handful of lights it buys nothing);
    True / False force it.  Call after beauty.configure_render (which switches it on)."""
    want = pre.get("light_tree") if isinstance(pre, dict) else None
    linked = []
    for o in S.bpy.data.objects:
        ll = getattr(o, "light_linking", None)
        if ll is not None and (ll.receiver_collection is not None or ll.blocker_collection is not None):
            linked.append(o.name)
    c = S.sc.cycles
    on = bool(want) if want is not None else not linked
    c.use_light_tree = on
    st = dict(use_light_tree=on, linked_lights=linked,
              reason="forced by preset" if want is not None else
              ("light linking present: Cycles light tree + linking is biased (+20 %) with fireflies"
               if linked else "no light linking"))
    if info is not None:
        info["light_tree"] = st
    return st


def load_lookdev(enabled=True):
    """The render.lookdev module (imported once, patches applied) or None if absent / disabled."""
    if not enabled or not LOOKDEV.exists():
        return None
    import_beauty()
    mod = importlib.import_module("render.lookdev")
    sys.modules.setdefault("lookdev", mod)
    return mod


def lookdev_status(mod, enabled=True):
    if not enabled:
        return dict(status="disabled (--no-lookdev)")
    if mod is None:
        return dict(status="absent (render/lookdev.py not found)")
    fn = next((f for f in LOOKDEV_FUNCS if callable(getattr(mod, f, None))), None)
    return dict(status="imported", module=str(LOOKDEV.relative_to(ROOT)), entry=fn)


def apply_lookdev(mod, **ctx):
    """Call lookdev's entry point with the context bound by parameter name (see module docstring).
    Returns a status dict for the sidecar JSON."""
    if mod is None:
        return None
    fname = next((f for f in LOOKDEV_FUNCS if callable(getattr(mod, f, None))), None)
    st = dict(status="imported", module=str(LOOKDEV.relative_to(ROOT)), entry=fname)
    if fname is None:
        st["status"] = "imported (no apply function: import-time patches only)"
        return st
    fn = getattr(mod, fname)
    if "bpy" not in ctx:
        try:
            import bpy
            ctx["bpy"] = bpy
        except Exception:
            pass
    if "materials" not in ctx and "bpy" in ctx:
        ctx["materials"] = ctx["bpy"].data.materials
    if "overrides" not in ctx and isinstance(ctx.get("pre"), dict):
        ctx["overrides"] = ctx["pre"].get("lookdev")
    if "bpy" in ctx:                     # the model paints the stroke outlines itself: no render-time ribbons on top
        B = import_beauty()
        if hasattr(B, "lookdev_overrides"):
            ctx["overrides"] = B.lookdev_overrides(ctx.get("overrides"))
    args, kwargs, used = [], {}, set()
    params = list(inspect.signature(fn).parameters.values())
    var_kw = any(p.kind is p.VAR_KEYWORD for p in params)
    for i, p in enumerate(params):
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        key = _ALIAS.get(p.name.lower())
        if key in ctx:
            val = ctx[key]
            used.add(key)
        elif p.default is not p.empty:
            continue
        elif i == 0 and "S" in ctx:
            val = ctx["S"]
            used.add("S")
        else:
            raise TypeError(f"render/lookdev.py:{fname}() needs parameter {p.name!r}, which the render "
                            f"drivers do not provide (have: {sorted(ctx)}); see render/hooks.py")
        if p.kind is p.POSITIONAL_ONLY:
            args.append(val)
        else:
            kwargs[p.name] = val
    if var_kw:
        for k, v in ctx.items():
            if k not in used and k not in kwargs:
                kwargs[k] = v
    res = fn(*args, **kwargs)
    st["status"] = "applied"
    if isinstance(res, dict):
        st["result"] = json.loads(json.dumps(res, default=str))
    return st


def apply_sets(presets: dict, names, sets):
    """beauty.py-style --set KEY=VALUE overrides (JSON values, dotted keys into nested dicts)."""
    for kv in sets or ():
        k, _, v = kv.partition("=")
        try:
            v = json.loads(v)
        except ValueError:
            pass
        for n in names:
            d = presets[n]
            *path, leaf = k.split(".")
            for q in path:
                d = d.setdefault(q, {})
            d[leaf] = v


def have_bpy():
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False
