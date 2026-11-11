.PHONY: install ingest index api ui eval eval-alerts eval-ablation eval-answers eval-answers-agent eval-stream plots test lint docker

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

eval-alerts:
	python eval/run_retrieval_eval.py --set alerts --modes bm25 dense hybrid hybrid+rerank+rrf graph

eval-ablation:
	python eval/run_ablation.py

eval-answers:
	python eval/run_answer_eval.py

eval-answers-agent:
	python eval/run_answer_eval.py --mode agent

eval-stream:
	python -u eval/run_stream_latency.py

plots:
	python eval/plot_results.py

test:
	pytest -q

lint:
	ruff check src tests app eval && ruff format --check src tests app eval

docker:
	docker compose up --build
