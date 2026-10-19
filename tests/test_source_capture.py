import json

import pytest

from scripts.import_source_capture import import_capture


def test_capture_import_checks_boundaries_overlap_and_preserves_raw(tmp_path):
    url = 'https://example.org/primary'
    one, two = tmp_path/'one.txt', tmp_path/'two.txt'
    one.write_text(url + '\nL10: Primary title\nL11: ' + 'source evidence ' * 40)
    two.write_text(url + '\nL11: ' + 'source evidence ' * 40 + '\nL12: End\nL13: Unrelated review')
    args = dict(url=url, first=10, last=12, title='Primary title')
    out = tmp_path/'source'
    doc = import_capture([one, two], out, **args)
    assert 'Unrelated review' not in doc['text']
    assert (out/'capture_0.txt').read_bytes() == one.read_bytes()
    assert json.loads((out/'text.json').read_text()) == doc
    with pytest.raises(ValueError, match='empty'):
        import_capture([one, two], out, **args)
    with pytest.raises(ValueError, match='gaps'):
        import_capture([one], tmp_path/'gap', **args)
    two.write_text(url + '\nL11: changed\nL12: End')
    with pytest.raises(ValueError, match='Conflicting'):
        import_capture([one, two], tmp_path/'conflict', **args)
