from scripts.benchmark_validity import semantic_agreement


def test_route_specific_target_requires_protocol_and_effect_agreement():
    protocol = dict(outcome='stay',unit='dimensionless',value_type='endpoint',measure='SMD',model='random',intervention_route='intravenous')
    synthesis = {'model':'random','effects':[dict(protocol)]}
    assert semantic_agreement(protocol,protocol,synthesis)['agrees']
    synthesis['effects'][0]['intervention_route'] = 'oral'
    assert not semantic_agreement(protocol,protocol,synthesis)['agrees']
    reference = {k:v for k,v in protocol.items() if k != 'intervention_route'}
    assert not semantic_agreement(protocol,reference,synthesis)['agrees']
