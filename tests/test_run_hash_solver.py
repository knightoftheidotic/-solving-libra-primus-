import subprocess
import sys
from pathlib import Path


def test_run_hash_solver_creates_output(tmp_path):
    # Run the script in an isolated temporary directory
    cwd = tmp_path
    # Locate repo root (parent of tests/) and script in repo root
    repo_root = Path(__file__).resolve().parents[1]
    repo_script = repo_root / "run_hash_solver.py"
    assert repo_script.exists(), "run_hash_solver.py must exist in repo root for test"

    # Copy sample inputs from repo into tempdir (preserve inputs/ folder)
    repo_inputs = repo_root / "inputs"
    if repo_inputs.exists():
        dest_inputs = cwd / "inputs"
        dest_inputs.mkdir(exist_ok=True)
        for p in repo_inputs.iterdir():
            dest = dest_inputs / p.name
            dest.write_text(p.read_text())

    # Execute the script
    result = subprocess.run([sys.executable, str(repo_script)], cwd=str(cwd))
    assert result.returncode == 0

    out_file = cwd / "out" / "results.json"
    assert out_file.exists()
    text = out_file.read_text()
    assert "hello" in text or "Solver ran" in text
