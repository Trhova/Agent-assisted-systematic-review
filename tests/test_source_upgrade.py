from scripts.model_backend import digest
from scripts.source_upgrade import upgrade_source


def test_image_table_failure_is_explicit_and_original_source_preserved(
    tmp_path, monkeypatch
):
    import scripts.source_upgrade as upgrade

    text = "Original trial body without image tables."
    (tmp_path / "article.xml").write_text(
        '<article><front><article-meta><contrib-group><contrib><name><surname>Researcher</surname><given-names>A</given-names></name></contrib></contrib-group></article-meta></front><body><table-wrap id="T1"><graphic/></table-wrap></body></article>'
    )
    monkeypatch.setattr(
        upgrade, "download_pdf", lambda *args: (False, {"status": "no_pdf"})
    )
    result = upgrade_source(
        {"pmcid": "PMC1", "id": "1"},
        tmp_path,
        {"text": text, "sha256": digest(text), "format": "JATS"},
    )
    assert "Researcher A" in result["text"]
    assert result["image_tables"] == ["T1"]
    assert result["table_recovery_error"]["status"] == "no_pdf"
    assert (tmp_path / ("text." + digest(text)[:12] + ".json")).exists()
