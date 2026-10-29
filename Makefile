.PHONY: install ingest index api ui eval test lint docker

install:
	pip install -e ".[dev]"

ingest:
	python -m threatlens.ingest.run

index:
	python -m threatlens.index.build

api:
	uvicorn threatlens.api:app --reload --port 8000

ui:
	streamlit run app/streamlit_app.py

eval:
	python eval/run_retrieval_eval.py

test:
	pytest -q

lint:
	ruff check src tests app eval && ruff format --check src tests app eval

docker:
	docker compose up --build
