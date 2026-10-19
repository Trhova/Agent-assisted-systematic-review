# Original-report page import v2

`import_source_pdf --pages FIRST LAST` accepts a contiguous one-based report range within an already retrieved public PDF collection. It first validates the original HTTP receipt, full collection checksum and PDF signature. It then derives the selected PDF, verifies the article DOI/title on its first page, and reparses only those pages with the standard parser. Both the whole retrieved collection and derived PDF are retained with exact hashes and page bounds; the unchanged HTTP receipt describes the collection, not a separate download of the derived PDF.

The caller must qualify original-report boundaries, including the final page. First-page identity alone does not establish complete article coverage. Other articles, commentary and aggregate review targets outside the selected range are excluded from model input. Original source files are never overwritten. This is acquisition provenance, not scientific eligibility or outcome adjudication.
