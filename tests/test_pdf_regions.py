from scripts.pdf_regions import column_regions


def test_full_width_header_and_figure_leave_narrative_columns_recoverable():
    chars = [{'x0':49,'x1':51,'top':0,'bottom':5,'text':'H'}]
    for i in range(10):
        for x in [10,70]:
            chars += [{'x0':x,'x1':x+5,'top':10+i*10,'bottom':15+i*10,'text':'x'}]*25
    chars += [{'x0':49,'x1':51,'top':120,'bottom':125,'text':'F'}]
    regions = column_regions(chars,(0,-20,100,200))
    assert len(regions) == 1
    assert regions[0][0] == (0,9.99,50.0,105.01)
    assert regions[0][1] == (50.0,9.99,100,105.01)
    assert column_regions(chars[:1],(0,-20,100,200)) == []
