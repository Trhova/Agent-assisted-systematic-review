import hashlib

import pytest

from scripts import pmc_cloud


def test_cloud_url_is_restricted_to_documented_bucket():
    assert (
        pmc_cloud.https_url("s3://pmc-oa-opendata/PMC1.1/a.pdf")
        == pmc_cloud.BASE + "PMC1.1/a.pdf"
    )
    with pytest.raises(ValueError):
        pmc_cloud.https_url("https://other.invalid/a.pdf")


def test_metadata_selects_published_version_not_largest_number(monkeypatch):
    class Response:
        content = b"<ListBucketResult><IsTruncated>false</IsTruncated><CommonPrefixes><Prefix>PMC1.1/</Prefix></CommonPrefixes><CommonPrefixes><Prefix>PMC1.2/</Prefix></CommonPrefixes></ListBucketResult>"

        def __init__(self, obj=None):
            self.obj = obj

        def json(self):
            return self.obj

    def response(url, **kwargs):
        if url == pmc_cloud.BASE:
            return Response()
        return Response(
            {
                "pmcid": "PMC1",
                "version": 1 if "PMC1.1" in url else 2,
                "is_manuscript": "PMC1.2" in url,
                "is_retracted": False,
            }
        )

    monkeypatch.setattr(pmc_cloud, "response", response)
    assert pmc_cloud.article_metadata("PMC1")["version"] == 1


def test_checksum_rejects_corrupted_pdf(monkeypatch):
    class Response:
        content = b"%PDF fixture"

    monkeypatch.setattr(pmc_cloud, "response", lambda *a, **kw: Response())
    url = pmc_cloud.BASE + "x.pdf?md5=" + hashlib.md5(Response.content).hexdigest()
    assert pmc_cloud.checked_bytes(url) == Response.content
    with pytest.raises(ValueError, match="MD5"):
        pmc_cloud.checked_bytes(pmc_cloud.BASE + "x.pdf?md5=incorrect")
