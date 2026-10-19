from scripts.openaire_sources import open_locations


def test_matching_doi_and_open_instance_required():
    def record(doi, access, url):
        return {
            "metadata": {
                "oaf:entity": {
                    "oaf:result": {
                        "pid": {"@classid": "doi", "$": doi},
                        "children": {
                            "result": {
                                "instance": {
                                    "accessright": {"@classid": access},
                                    "webresource": {"url": {"$": url}},
                                }
                            }
                        },
                    }
                }
            }
        }

    payload = {
        "response": {
            "results": {
                "result": [
                    record("10.1/A", "OPEN", "https://institution.edu/paper.pdf"),
                    record("10.1/B", "OPEN", "https://institution.edu/wrong.pdf"),
                    record("10.1/A", "CLOSED", "https://institution.edu/closed.pdf"),
                ]
            }
        }
    }
    assert open_locations(payload, "10.1/a") == ["https://institution.edu/paper.pdf"]
