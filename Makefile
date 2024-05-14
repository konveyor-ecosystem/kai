CONTAINER_RUNTIME = podman

CWD := $(shell pwd)
KAI_PYTHON_PATH="$(CWD)/kai:$(PYTHONPATH)"
LOGLEVEL ?= info
NUM_WORKERS ?= 8
DEMO_MODE ?= False
DROP_TABLES ?= False

run-postgres:
	$(CONTAINER_RUNTIME) run -it -v data:/var/lib/postgresql/data -e POSTGRES_USER=kai -e POSTGRES_PASSWORD=dog8code -e POSTGRES_DB=kai -p 5432:5432 docker.io/pgvector/pgvector:pg15

# Can adjust logging level by defining env var: KAI_LOG_LEVEL
run-server:
	PYTHONPATH=$(KAI_PYTHON_PATH) gunicorn --timeout 3600 -w $(NUM_WORKERS) --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker 'kai.server:app("$(LOGLEVEL)", $(DEMO_MODE))'

load-data:
	PYTHONPATH=$(KAI_PYTHON_PATH) python ./kai/service/incident_store/psql.py  --config_filepath ./kai/config.toml --drop_tables $(DROP_TABLES)