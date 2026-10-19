"""Evidence-only continuation for verified semantics blocked by literal anchors."""
import copy
import json

from scripts.family_adjudication import VERIFY, contains
from scripts.family_evidence_tiers import RULE, decide

POLICY = 'family_evidence_tiers_v2_exact_quotes_v1'


def apply_quotes(proposal, repair, sources):
    if set(repair)!={'features'} or not isinstance(repair['features'],list) or len(repair['features'])!=len(proposal['features']):
        raise ValueError('Exact fixed feature count required')
    result=copy.deepcopy(proposal)
    for original,new in zip(result['features'],repair['features']):
        if set(new)!={'evidence_a','evidence_b'}:
            raise ValueError('Only paired evidence strings may change')
        for name,source in zip(('evidence_a','evidence_b'),sources):
            if not isinstance(new[name],str) or not contains(source,new[name]):
                raise ValueError('Every feature anchor must match exact source')
            original[name]=new[name]
    return result


def repair_link(link,sources,call):
    """Never repair an adverse/uncertain scientific verdict into a positive one."""
    if link.get('independently_verified') and link.get('source_features_valid'):
        return copy.deepcopy(link)
    if link.get('source_features_valid') is not False or link.get('verification',{}).get('valid') is not True:
        return copy.deepcopy(link)
    proposal=link['evidence_tier_assessment'];n=len(proposal['features'])
    schema={'type':'object','additionalProperties':False,'required':['features'],'properties':{'features':{
        'type':'array','minItems':n,'maxItems':n,'items':{'type':'object','additionalProperties':False,
        'required':['evidence_a','evidence_b'],'properties':{'evidence_a':{'type':'string'},'evidence_b':{'type':'string'}}}}}}
    context='\nREPORT A:\n'+sources[0]+'\nREPORT B:\n'+sources[1]
    revised=copy.deepcopy(link);revised['prior_quote_blocked_assessment']=copy.deepcopy(link)
    revised['quote_repair_policy']=POLICY
    try:
        quotes=call('Repair ONLY the literal source strings in these fixed ordered features. Return one evidence_a/evidence_b object per feature, in exactly the same order. Each value must be ONE contiguous substring copied verbatim from its corresponding source, apart from whitespace. Do NOT add enclosing quotation marks, parentheses, report/page/section labels, explanations, ellipses, or joined fragments. Do not reproduce such formatting from the failed strings. Preserve literal source punctuation and reading order. Do not change feature domains, study identity, participant-reuse judgment, reason or limitations. If a feature has no supporting exact substring, use an empty string; validation will withhold the comparison.\nFIXED PROPOSAL:\n'+json.dumps(proposal)+context,schema)
        revised['quote_repair_proposal']=quotes
        fixed=apply_quotes(proposal,quotes,sources)
        verification=call(RULE+'\nIndependently reverify this fixed scientific proposal and newly anchored evidence against both entire sources. Exact substring matching alone is not scientific entailment. Reject any feature or identity/reuse conclusion not supported by its quoted original and full context.\nPROPOSAL:\n'+json.dumps(fixed)+context,VERIFY)
        revised.update(decide(fixed,sources,verification))
    except Exception as error:  # noqa: BLE001 - model/adapter failure must preserve a blocking result
        revised.update(relationship='unclear',independently_verified=False,reason=str(error))
    return revised
