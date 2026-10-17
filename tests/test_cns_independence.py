"""TIE is independent of CNS, and these tests hold whether or not CNS is installed.

Each runs in a fresh interpreter in which ``cns`` is blocked outright
(``sys.modules['cns'] = None`` makes any import of it fail), so the result does not
depend on what the test environment happens to contain. They never skip.
"""
import ast
import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE = SRC / "tie"
BLOCK = "import sys; sys.modules['cns'] = None; sys.modules['cns.gate'] = None\n"
ENV = {"PYTHONPATH": str(SRC), "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
HINT = "pip install 'tie-transcript-intelligence-engine[cns]'"
PIPELINE = """
    from tie import (EpistemicStatus, build_package, create_source, evidence_from_statement,
                     reconstruct_summary, segment_source)
    source = create_source("s", "A statement worth keeping.")
    coverage = segment_source(source, max_chars=100)
    evidence = evidence_from_statement(source, evidence_id="e", statement="A statement worth keeping.",
                                       epistemic_status=EpistemicStatus.EXPLICIT,
                                       segment_id=coverage.segments[0].segment_id)
    rec = reconstruct_summary(reconstruction_id="r", evidence=(evidence,), provenance=source.provenance)
    package = build_package(package_id="p", source=source, coverage=coverage, evidence=(evidence,), reconstruction=rec)
"""


def run(code: str, *, block: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", (BLOCK if block else "") + textwrap.dedent(code)],
                          capture_output=True, text=True, env=ENV, timeout=120)


def ok(done: subprocess.CompletedProcess) -> None:
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().endswith("ok"), done.stdout


def test_the_package_and_its_connector_import_with_cns_blocked():
    ok(run("import tie, tie.cns_connector; print('ok')"))


def test_the_pipeline_still_does_its_job_with_cns_blocked():
    ok(run(PIPELINE + """
    assert package.validation.valid and package.typed_handoff.evidence_ids == ("e",)
    assert package.to_dict()["package_id"] == "p"
    print('ok')
    """))


def test_the_connector_says_what_is_missing_when_cns_is_blocked():
    ok(run(PIPELINE + f"""
    from tie.cns_connector import (CnsNotInstalled, binds, cns_available, handoff_digest, package_content,
                                   package_digest)
    assert cns_available() is False
    assert package_content(package)["package_id"] == "p"   # plain data, no cns needed
    for call in (lambda: package_digest(package), lambda: handoff_digest(package.typed_handoff),
                 lambda: binds(object(), package)):
        try:
            call()
        except CnsNotInstalled as e:
            assert {HINT!r} in str(e)
            assert isinstance(e, ImportError)
        else:
            raise SystemExit("ran without cns")
    print('ok')
    """))


def test_importing_the_package_does_not_load_cns_even_when_it_is_installed():
    ok(run("""
        import sys
        import tie, tie.cns_connector
        assert not [m for m in sys.modules if m == "cns" or m.startswith("cns.")], "cns was loaded"
        print('ok')
    """, block=False))


def test_no_module_of_the_package_imports_cns_by_statement():
    offenders = {}
    for path in PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else []
            bad = [n for n in names if n == "cns" or n.startswith("cns.")]
            if bad:
                offenders.setdefault(str(path.relative_to(PACKAGE)), []).extend(bad)
    assert offenders == {}


def test_the_package_declares_no_runtime_dependency_and_pins_the_cns_extra():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert meta["dependencies"] == []
    assert meta["optional-dependencies"]["cns"] == ["cns @ git+https://github.com/wking53214/CNS.git@v1.8.0"]
