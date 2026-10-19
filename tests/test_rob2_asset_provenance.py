from pathlib import Path

from scripts import model_backend, pdf_layout, rob2_draft


def test_assets_use_loaded_modules_not_cwd_decoys(tmp_path, monkeypatch):
    root = Path.cwd()
    for asset in rob2_draft.ASSETS:
        dest = tmp_path / asset
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((root / asset).read_bytes())
    (tmp_path / "scripts").mkdir()
    for name in ("pdf_layout", "model_backend"):
        (tmp_path / "scripts" / (name + ".py")).write_text("DECOY")
    monkeypatch.chdir(tmp_path)
    assets = rob2_draft.load_assets()
    assert assets["scripts/pdf_layout.py"] == Path(pdf_layout.__file__).read_text()
    assert assets["scripts/model_backend.py"] == Path(model_backend.__file__).read_text()
