"""Writes data/sfo_stands.json/.js - since 24 Sep 2026 a thin wrapper around tools/stands/build_stands.py, which
rebuilds the stands and jet bridges from OSM lead-ins, SFO's stand names, NAIP 2024 and ADS-B
(docs/research/stands_rebuild.md). The earlier export of the Google-screenshot survey (stand_defs.py) lives on as
export_stands_google_legacy.py and no longer writes data/.
Usage: python3 tools/sat/export_stands.py   (same as python3 tools/stands/build_stands.py)"""
import os, runpy, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stands')
sys.path.insert(0, HERE); os.chdir(HERE)
runpy.run_path(os.path.join(HERE, 'build_stands.py'), run_name='__main__')
