"""Launch a CLI attempt from an immutable local copy of its Python sources."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.model_backend import atomic_json, digest


def bundle(source_directory, bundle_root):
    sources = {p.name: p.read_text() for p in Path(source_directory).glob("*.py")}
    identity = digest(sources)
    root = Path(bundle_root) / identity
    package = root / "scripts"
    package.mkdir(parents=True, exist_ok=True)
    for name, text in sources.items():
        target = package / name
        if target.exists() and target.read_text() != text:
            raise ValueError("Immutable code bundle mismatch")
        if not target.exists():
            with tempfile.NamedTemporaryFile(
                mode="w", dir=package, prefix=name + ".", delete=False
            ) as handle:
                handle.write(text)
                temporary = Path(handle.name)
            temporary.replace(target)
    atomic_json(root / "manifest.json", {"sha256": identity, "files": sorted(sources)})
    return root.resolve(), identity


def command(root, identity, module, argv):
    """Verify the entire pinned package before importing a nested CLI."""
    code = (
        "import hashlib,json,pathlib,sys,runpy; "
        "root=pathlib.Path(sys.argv.pop(1)); expected=sys.argv.pop(1); "
        "module=sys.argv.pop(1); "
        "sources={p.name:p.read_text() for p in (root/'scripts').glob('*.py')}; "
        "actual=hashlib.sha256(json.dumps(sources,sort_keys=True,ensure_ascii=False).encode()).hexdigest(); "
        "\nif actual != expected: raise SystemExit('Frozen child code checksum differs')\n"
        "sys._asr_frozen_code=actual; sys.path.insert(0,str(root)); runpy.run_module(module,run_name='__main__')"
    )
    return [sys.executable, "-c", code, str(root), identity, module, *argv]


def launch(argv):
    root, _ = bundle(Path(__file__).parent, Path("data/benchmarks/code_bundles"))
    # Preserve repository cwd for source data while putting the frozen package first.
    code = "import sys; sys.path.insert(0, sys.argv.pop(1)); from scripts.autonomous_review import main; main()"
    return subprocess.run(
        [sys.executable, "-c", code, str(root), *argv], check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(launch(sys.argv[1:]))
