"""Committed example outputs match what the example scripts produce today."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parents[1] / "examples"

#: (script, arguments, committed outputs), paths relative to ``examples/``.
CASES = [
    ("brick/quickstart/brick_quickstart.py", (), ("bldg1.ttl",)),
    ("s223/ahu/s223_quickstart.py", (), ("ahu.ttl", "ahu_schema.ttl")),
    (
        "s223/cooling_coil/cooling_coil.py",
        (),
        ("cooling_coil.ttl", "cooling_coil_schema.ttl"),
    ),
    ("watr/asm2d/watertap_asm2d.py", (), ("asm2d.ttl",)),
    (
        "watr/epanet_anytown/epanet_anytown_to_watr.py",
        ("Anytown.inp",),
        ("anytown_watr.ttl",),
    ),
    ("watr/seawater_ro/watertap_seawater_ro_full.py", (), ("seawater_ro_full.ttl",)),
    (
        "watr/seawater_ro_pretreatment/watertap_seawater_ro_pretreatment.py",
        (),
        ("seawater_ro_pretreatment.ttl",),
    ),
    ("watr/treatment/watr_quickstart.py", (), ("treatment.ttl",)),
]


@pytest.mark.parametrize(
    ("script", "args", "outputs"), CASES, ids=[case[0] for case in CASES]
)
def test_committed_example_output_is_current(script, args, outputs, tmp_path):
    source = EXAMPLES / script
    workdir = tmp_path / source.parent.name
    shutil.copytree(source.parent, workdir)
    subprocess.run(
        [sys.executable, source.name, *args],
        cwd=workdir,
        check=True,
        capture_output=True,
    )
    for output in outputs:
        committed = (source.parent / output).read_text()
        assert (workdir / output).read_text() == committed, (
            f"examples/{Path(script).parent / output} is stale; "
            "regenerate with `make examples`"
        )


def test_every_example_script_is_covered():
    scripts = {
        str(path.relative_to(EXAMPLES))
        for path in EXAMPLES.rglob("*.py")
        if "Produces" in path.read_text() or ".save(" in path.read_text()
    }
    assert scripts <= {case[0] for case in CASES}
