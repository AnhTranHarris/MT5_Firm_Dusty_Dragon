from pathlib import Path

from dusty_dragon.qc.local import QcCommand, build_qc_plan, run_qc


def test_qc_plan_without_install_matches_ci_quality_steps() -> None:
    assert build_qc_plan(install=False) == (
        QcCommand(name="ruff", argv=("ruff", "check", ".")),
        QcCommand(name="pytest", argv=("pytest",)),
    )


def test_qc_plan_with_install_starts_with_editable_dev_install() -> None:
    plan = build_qc_plan(install=True)

    assert plan[0].name == "install"
    assert plan[0].argv[-3:] == ("install", "-e", ".[dev]")


def test_run_qc_stops_after_first_failure(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv, *, cwd):
        calls.append(tuple(argv))
        assert cwd == Path("repo")
        return 7

    monkeypatch.setattr("dusty_dragon.qc.local._run", fake_run)

    assert run_qc(repository_root=Path("repo"), install=False) == 7
    assert calls == [("ruff", "check", ".")]
