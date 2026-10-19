import json

import pytest

from scripts.primary_image_queue import sha
from scripts.report_chronology import assess


def case(tmp_path,date='2016/10/18',extra=''):
    html=tmp_path/'publisher.html';html.write_text('<meta name="citation_doi" content="10.1007/example"><meta name="citation_online_date" content="'+date+'"><meta name="citation_publication_date" content="2017/03">'+extra)
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps({'status':200,'sha256':sha(html),'url':'https://publisher.example/article'}));return html,receipt


def test_online_date_not_issue_or_trial_date(tmp_path):
    h,r=case(tmp_path,extra='Trial conducted2013; references2010')
    assert assess(h,r,'10.1007/example','2016-04-12')['status']=='after_cutoff'
    assert assess(h,r,'10.1007/example','2016-10-18')['status']=='on_or_before_cutoff'


@pytest.mark.parametrize('date',['2016','2016/10','2016/13/40','unknown'])
def test_partial_or_invalid_date_unresolved(tmp_path,date):
    h,r=case(tmp_path,date);assert assess(h,r,'10.1007/example','2016-04-12')['status']=='unresolved_publication_date'


def test_conflicting_dates_unresolved(tmp_path):
    h,r=case(tmp_path,extra='<meta name="citation_online_date" content="2016/03/01">');assert assess(h,r,'10.1007/example','2016-04-12')['status']=='unresolved_publication_date'


def test_identity_and_source_tamper(tmp_path):
    h,r=case(tmp_path)
    with pytest.raises(ValueError):assess(h,r,'other','2016-04-12')
    h.write_text('different')
    with pytest.raises(ValueError):assess(h,r,'10.1007/example','2016-04-12')
