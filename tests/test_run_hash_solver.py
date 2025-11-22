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

    # Execute the script
    result = subprocess.run([sys.executable, str(repo_script)], cwd=str(cwd))
    assert result.returncode == 0

    out_file = cwd / "out" / "result.txt"
    assert out_file.exists()
    text = out_file.read_text()
    assert "Solver ran" in text
