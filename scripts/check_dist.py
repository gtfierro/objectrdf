"""Smoke-test an installed objectrdf wheel before upload.

``make dist-check`` runs this in a throwaway environment that has only the
built wheel installed, so it catches files missing from the distribution
rather than from the source tree.
"""

from importlib import resources
from pathlib import Path

import objectrdf
from objectrdf import Model, connect, watr

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "brick",
    "s223",
    "s223.hvac",
    "watr",
    "watr.asm2d",
    "watr.drinking_water",
    "watr.seawater_ro",
)


def main() -> None:
    installed = Path(objectrdf.__file__).resolve()
    if installed.is_relative_to(ROOT / "src"):
        raise SystemExit(f"imported the source tree, not the wheel: {installed}")

    for name in PACKAGES:
        shapes = resources.files(f"objectrdf.{name}") / "_shapes.ttl"
        if not shapes.is_file():
            raise SystemExit(f"objectrdf.{name} is missing _shapes.ttl")
    if not (resources.files("objectrdf") / "py.typed").is_file():
        raise SystemExit("objectrdf is missing py.typed")

    with Model("urn:example/dist-check#") as model:
        clarifier = watr.Clarifier("clarifier")
        connect(watr.Chiller("source"), watr.Pump("pump"))
        connect(model["pump"], watr.Tank("tank"))
    if watr.Process_Settling not in clarifier.has_process:
        raise SystemExit("class defaults were not applied")
    model.resolve()
    model.validate()

    print(f"objectrdf {objectrdf.__version__} wheel OK ({installed.parent})")


if __name__ == "__main__":
    main()
