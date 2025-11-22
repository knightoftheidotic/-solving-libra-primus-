#!/usr/bin/env python3
"""Safe placeholder for the real hash solver.

This script creates an `out/` directory and writes a small result file so
the GitHub Actions workflow has an artifact to upload during testing.
"""
import os
import sys
from pathlib import Path

def main():
    wd = os.environ.get("WORKING_DIR", os.getcwd())
    print(f"Working dir: {wd}")
    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    result_file = out_dir / "result.txt"

    use_tor = os.environ.get("USE_TOR", "0").strip()
    if use_tor == "1":
        # Safety check: refuse to silently enable Tor on unknown runners.
        # The workflow is set up to only start Tor on self-hosted runners.
        print("USE_TOR=1 detected. Ensure you're running on a self-hosted runner you control.")
        print("This placeholder will not perform any network actions.")

    with result_file.open("w") as f:
        if use_tor == "1":
            f.write("Solver ran (Tor mode enabled).\n")
        else:
            f.write("Solver ran successfully.\n")

    print(f"Wrote {result_file}")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print("Error running placeholder solver:", e)
        sys.exit(2)
