from src.validation.run_all import run_validation_runner


def test_validation_runner_smoke(tmp_path):
    report = run_validation_runner(write_reports=False, reports_dir=str(tmp_path))
    assert report["schema_version"] == 1
    assert "metrics" in report
    assert "lineage" in report
    assert "block_rows" in report["metrics"]

