"""Receipt-bound publisher publication chronology; never infer dates from trial dates."""
import argparse
import datetime as dt
import json
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.model_backend import atomic_json
from scripts.primary_image_queue import sha


def assess(html, receipt, doi, cutoff):
    html,receipt=Path(html),Path(receipt)
    r=json.loads(receipt.read_text())
    if r.get('status')!=200 or r.get('sha256')!=sha(html):raise ValueError('Successful exact publisher receipt required')
    soup=BeautifulSoup(html.read_bytes(),'html.parser')
    metadata={}
    for m in soup.find_all('meta',attrs={'name':True,'content':True}):metadata.setdefault(m['name'].lower(),set()).add(m['content'])
    if metadata.get('citation_doi')!={doi}:raise ValueError('Publisher DOI differs or ambiguous')
    dates=metadata.get('citation_online_date',set())
    if len(dates)!=1:
        return {'status':'unresolved_publication_date','reason':'Exactly one explicit online date required; issue/trial dates are not substituted','doi':doi}
    raw=next(iter(dates))
    try:
        if len(raw)!=10:raise ValueError('Exact day required')
        date=dt.date.fromisoformat(raw.replace('/','-'));limit=dt.date.fromisoformat(cutoff)
    except ValueError:
        return {'status':'unresolved_publication_date','reason':'Invalid or partial day-level publication date','doi':doi}
    return {'status':'after_cutoff' if date>limit else 'on_or_before_cutoff','doi':doi,'publication_date':date.isoformat(),'cutoff':cutoff,'evidence':{'raw_value':raw,'locator':'meta[name=citation_online_date]','html_sha256':sha(html),'receipt_sha256':sha(receipt),'url':r.get('final_url',r.get('url'))},'scope':'Report chronology only; no trial-family, outcome or whole-review eligibility decision.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--html',required=True);p.add_argument('--receipt',required=True);p.add_argument('--doi',required=True);p.add_argument('--cutoff',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.output).exists():raise ValueError('Use new output')
    result=assess(a.html,a.receipt,a.doi,a.cutoff);atomic_json(a.output,result);print(json.dumps(result,indent=2))
