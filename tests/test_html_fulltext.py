from scripts.html_fulltext import extract_html

RECORD = {
    "id": "123",
    "title": "A randomized trial with a sufficiently long scientific title",
    "doi": "10.1234/trial",
}


def page(headings, doi="10.1234/trial"):
    return (
        f'<html><head><meta name="citation_doi" content="{doi}"><meta name="citation_title" content="{RECORD["title"]}"></head><body><article>'
        + headings
        + "<p>"
        + "Primary article narrative. " * 250
        + '</p><table><caption>Reported endpoint</caption><tr><th>Arm</th><th>Mean ± SD</th></tr><tr><td>Control</td><td>12 ± 3</td></tr></table><section id="ref-list1">Cited unrelated trial 99 ± 88</section></article></body></html>'
    ).encode()


def test_full_article_preserves_table_cells_and_raw_provenance():
    raw = page("<h2>Materials and methods</h2><h2>Results</h2>")
    doc = extract_html(RECORD, raw, "https://example.org/article")
    assert doc is not None
    assert "Control | 12 ± 3" in doc["text"]
    assert "Cited unrelated trial" not in doc["text"]
    assert doc["html_sha256"] and doc["identity"]["doi_metadata"]


def test_structured_abstract_on_long_landing_page_is_not_fulltext():
    raw = page(
        "<h2>Abstract</h2><h3>Methods</h3><h3>Results</h3><h2>Access options</h2>"
    )
    assert extract_html(RECORD, raw, "https://example.org/article") is None


def test_conflicting_doi_rejected_even_with_matching_title():
    raw = page("<h2>Methods</h2><h2>Results</h2>", doi="10.1234/other")
    assert extract_html(RECORD, raw, "https://example.org/article") is None


def test_whole_site_without_scientific_article_container_is_rejected():
    raw = (
        page("<h2>Methods</h2><h2>Results</h2>")
        .replace(b"<article>", b"<main>")
        .replace(b"</article>", b"</main>")
    )
    assert extract_html(RECORD, raw, "https://example.org/article") is None


def test_abstract_with_h2_subheadings_still_is_not_a_full_article():
    raw = page(
        '<section class="abstract"><h2>Methods</h2><h2>Results</h2></section><h2>Access options</h2>'
    )
    assert extract_html(RECORD, raw, "https://example.org/article") is None
