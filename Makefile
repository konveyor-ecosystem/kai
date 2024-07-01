CONTAINER_RUNTIME = podman

CWD := $(shell pwd)
KAI_PYTHON_PATH="$(CWD)/kai:$(PYTHONPATH)"
LOGLEVEL ?= info
NUM_WORKERS ?= 8
DEMO_MODE ?= False
DROP_TABLES ?= False
HUB_URL ?= ""
IMPORTER_ARGS ?= ""

run-postgres:
	$(CONTAINER_RUNTIME) run -it -v data:/var/lib/postgresql/data -e POSTGRES_USER=kai -e POSTGRES_PASSWORD=dog8code -e POSTGRES_DB=kai -p 5432:5432 docker.io/library/postgres:16.3

run-server:
	PYTHONPATH=$(KAI_PYTHON_PATH) LOGLEVEL=$(LOGLEVEL) DEMO_MODE=$(DEMO_MODE) gunicorn --timeout 3600 -w $(NUM_WORKERS) --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker 'kai.server:app()'

run-konveyor-importer:
	PYTHONPATH=$(KAI_PYTHON_PATH) python ./kai/hub_importer.py --loglevel ${LOGLEVEL} --config_filepath ./kai/config.toml ${IMPORTER_ARGS} ${HUB_URL}

load-data:
	PYTHONPATH=$(KAI_PYTHON_PATH) python ./kai/service/incident_store/psql.py  --config_filepath ./kai/config.toml --drop_tables $(DROP_TABLES)
