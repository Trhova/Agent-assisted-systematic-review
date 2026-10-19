import json

import pytest

from scripts.bibliographic_supplement import load
from scripts.model_backend import digest


def test_frozen_leads_are_bibliographic_not_numeric(tmp_path):
    row = {'id': 'doi-example', 'doi': '10.1/example', 'title': 'Example trial', 'discovery_source': 'publisher', 'source_urls': ['https://example.org/paper.pdf']}
    path = tmp_path/'leads.json'
    path.write_text(json.dumps([row]))
    protocol = {'bibliographic_supplement': {'path': str(path), 'sha256': digest([row])}}
    assert load(protocol, tmp_path/'run') == [row]
    row['mean_treatment'] = 7
    path.write_text(json.dumps([row]))
    with pytest.raises(ValueError, match='checksum'):
        load(protocol, tmp_path/'run')
    protocol['bibliographic_supplement']['sha256'] = digest([row])
    with pytest.raises(ValueError, match='bibliographic'):
        load(protocol, tmp_path/'run')


def test_primary_report_without_assigned_doi(tmp_path):
    row = {'id': 'journal-2013-trial', 'title': 'Original primary trial',
           'discovery_source': 'Journal archive', 'doi': '',
           'source_urls': ['https://example.org/article.pdf']}
    path = tmp_path/'leads.json'
    path.write_text(json.dumps([row]))
    protocol = {'bibliographic_supplement': {'path': str(path), 'sha256': digest([row])}}
    assert load(protocol, tmp_path/'run') == [row]
    row['source_urls'] = []
    path.write_text(json.dumps([row]))
    protocol['bibliographic_supplement']['sha256'] = digest([row])
    with pytest.raises(ValueError, match='DOI or primary source URL'):
        load(protocol, tmp_path/'run')
