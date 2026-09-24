"""Stand / bridge plausibility checks of data/sfo_stands.json - since 24 Sep 2026 a wrapper around
tools/stands/check_stands.py (aircraft vs building, aircraft vs aircraft (non-exclusive pairs; physical 3 m, ICAO
clearances as notes), aircraft on paved ground (NAIP), bridge reach and crossings). The checks of the old
Google-screenshot survey are check_google_legacy.py / check_bridges_google_legacy.py.
Usage: python3 tools/sat/check.py  (or check_bridges.py; both run the full check)"""
import os, runpy, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stands')
sys.path.insert(0, HERE); os.chdir(HERE)
runpy.run_path(os.path.join(HERE, 'check_stands.py'), run_name='__main__')
