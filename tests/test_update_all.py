import sys

sys.path.insert(0, "scripts")
import update_all


def test_fail_soft_continues():
    def boom():
        raise RuntimeError("network down")
    statuses = update_all.run_all({"ok": lambda: True, "boom": boom, "dup": lambda: False})
    assert statuses["ok"] == "appended"
    assert statuses["dup"] == "skipped (dup)"
    assert statuses["boom"].startswith("FAILED")


def test_reassess_runs_fairprice():
    calls = []
    assert update_all.reassess(lambda: calls.append(1)) == "reassessed"
    assert calls == [1]


def test_reassess_skips_without_passphrase(capsys):
    def boom():
        raise RuntimeError("IMOBILIEN_KEY not set (env var or .env)")
    status = update_all.reassess(boom)  # must not propagate: a refresh still succeeded
    assert status.startswith("skipped")
    assert "IMOBILIEN_KEY" in status
    out = capsys.readouterr().out
    assert "fair price: SKIPPED" in out
    assert "scripts/fairprice.py" in out
