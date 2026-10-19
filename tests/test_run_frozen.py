from scripts.run_frozen import bundle


def test_bundle_is_immutable_when_checkout_changes(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "__init__.py").write_text("")
    (source / "worker.py").write_text("value = 1\n")
    first, identity = bundle(source, tmp_path / "bundles")
    (source / "worker.py").write_text("value = 2\n")
    second, other = bundle(source, tmp_path / "bundles")
    assert identity != other and first != second
    assert (first / "scripts/worker.py").read_text() == "value = 1\n"
    assert (second / "scripts/worker.py").read_text() == "value = 2\n"


def test_concurrent_launchers_share_bundle_without_temporary_file_race(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    source = tmp_path / "source"
    source.mkdir()
    for i in range(20):
        (source / f"module{i}.py").write_text(f"value = {i}\n")
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(lambda _: bundle(source, tmp_path / "bundles"), range(8))
        )
    assert len({str(root) for root, identity in results}) == 1
    assert len(list((results[0][0] / "scripts").iterdir())) == 20
