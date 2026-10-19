import json
import pytest
from scripts.import_model_cache import import_cache
from scripts.model_backend import digest, atomic_json


def setup(tmp_path):
    req = {'model': 'pinned', 'backend': 'codex', 'prompt': 'test', 'schema': {'type': 'object', 'required': ['ok'], 'properties': {'ok': {'type': 'boolean'}}}}
    source = tmp_path/'source'; folder=source/digest(req)
    atomic_json(folder/'request.json', req); atomic_json(folder/'parsed.json', {'ok': True})
    event={'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'ok':True})}}
    atomic_json(folder/'1.response.json', {'returncode':0,'stdout':json.dumps(event)})
    return source,folder


def test_success_bound_to_actual_response_and_failed_requests_not_imported(tmp_path):
    source,folder=setup(tmp_path); (source/'failed').mkdir()
    r=import_cache(source,tmp_path/'dest',model='pinned',backend='codex')
    assert len(r['verified'])==1 and r['skipped_without_success']==['failed']
    assert (tmp_path/'dest'/folder.name/'parsed.json').exists()


def test_fabricated_parsed_result_or_model_change_refused(tmp_path):
    source,folder=setup(tmp_path)
    with pytest.raises(ValueError,match='policy differs'):
        import_cache(source,tmp_path/'dest',model='other',backend='codex')
    atomic_json(folder/'parsed.json', {'ok':False})
    with pytest.raises(ValueError,match='receipt'):
        import_cache(source,tmp_path/'dest',model='pinned',backend='codex')
    assert not (tmp_path/'dest').exists()
