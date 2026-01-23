.PHONY: setup search table screen_abstracts pdfs extract rob2 export all smoke_no_llm smoke_llm

PYTHON ?= python3
VENV ?= .venv

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -e .[dev]

search:
	$(VENV)/bin/$(PYTHON) scripts/00_search_pubmed.py --protocol protocol/protocol.yaml

table:
	$(VENV)/bin/$(PYTHON) scripts/01_build_table.py --protocol protocol/protocol.yaml

pdfs:
	$(VENV)/bin/$(PYTHON) scripts/02_download_pdfs.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet

screen_abstracts:
	$(VENV)/bin/$(PYTHON) scripts/03_screen_abstracts_llm.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet

extract:
	$(VENV)/bin/$(PYTHON) scripts/04_extract_fulltext_llm.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet

rob2:
	$(VENV)/bin/$(PYTHON) scripts/05_rob2_llm.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet

export:
	$(VENV)/bin/$(PYTHON) scripts/06_apply_overrides_and_export.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet

all: search table screen_abstracts pdfs extract rob2 export

smoke_no_llm:
	$(VENV)/bin/$(PYTHON) scripts/00_search_pubmed.py --protocol protocol/protocol.yaml --retmax 10 --limit 10 --overwrite
	$(VENV)/bin/$(PYTHON) scripts/01_build_table.py --protocol protocol/protocol.yaml --overwrite
	$(VENV)/bin/$(PYTHON) scripts/06_apply_overrides_and_export.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet --overwrite

smoke_llm:
	$(VENV)/bin/$(PYTHON) scripts/03_screen_abstracts_llm.py --protocol protocol/protocol.yaml --table data/outputs/screening_table.parquet --limit 3 --overwrite
