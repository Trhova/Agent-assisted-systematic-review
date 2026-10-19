import pytest
import yaml

from scripts.benchmark_suite import suite


@pytest.mark.parametrize('specified', [{'prespecified_model': 'other-model'}, {'prespecified_backend': 'openai'}])
def test_suite_rejects_model_or_backend_substitution_before_execution(tmp_path, specified):
    config = tmp_path/'suite.yaml'
    config.write_text(yaml.safe_dump(specified))
    with pytest.raises(ValueError, match='prespecified'):
        suite(config, tmp_path/'run', model='gpt-6-astra', backend='codex')
    assert not (tmp_path/'run').exists()
