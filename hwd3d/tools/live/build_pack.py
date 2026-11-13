#!/usr/bin/env python3
"""Alias of tools/live/build_replay.py under the name docs/phase2_fork_map.md 2.2 uses (same arguments, same outputs in
hwd3d/out/replay/). See build_replay.py for the format, the D1 rules and the windows."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_replay  # noqa: E402

if __name__ == '__main__':
    build_replay.main()
