import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_reads_json_writes_json(tmp_path):
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"shipments": [{"id": "a", "number": "080-38652331"}]}),
                   encoding="utf-8")
    out = tmp_path / "out.json"
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    subprocess.run(
        [sys.executable, "-m", "tracking_agent.cli",
         "--input", str(inp), "--output", str(out)],
        check=True,
        cwd=str(repo_root),
        env=env,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["total"] == 1
    assert data["results"][0]["input"]["number"] == "080-38652331"


def test_cli_reads_csv_prints_json(tmp_path):
    inp = tmp_path / "in.csv"
    inp.write_text("id,number\nb1,TLLU4912250\n", encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, "-m", "tracking_agent.cli", "--input", str(inp)],
        check=True,
        capture_output=True,
        cwd=str(repo_root),
        env=env,
    )
    data = json.loads(result.stdout.decode("utf-8"))
    assert data["summary"]["total"] == 1


def test_cli_invalid_number_produces_error(tmp_path):
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"shipments": [{"id": "x", "number": "bad-number"}]}),
                   encoding="utf-8")
    out = tmp_path / "out.json"
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    subprocess.run(
        [sys.executable, "-m", "tracking_agent.cli",
         "--input", str(inp), "--output", str(out)],
        check=True,
        cwd=str(repo_root),
        env=env,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["results"][0]["errors"][0]["code"] == "INVALID_FORMAT"
