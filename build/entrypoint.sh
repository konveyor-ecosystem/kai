#!/bin/bash

# If we are using compose.yml use the repo config.toml
if [ -f /podman_compose/kai/config.toml ]; then
  cp /podman_compose/kai/config.toml /kai/kai/config.toml
  sed -i 's/^host\ =.*/host = "kai_db"/g' /kai/kai/config.toml
  sed -i "s/^database =.*/database = \"$POSTGRES_DB\"/g" /kai/kai/config.toml
  sed -i "s/^user =.*/user = \"$POSTGRES_USER\"/g" /kai/kai/config.toml
  sed -i "s/^password =.*/password =\"$POSTGRES_PASSWORD\"/g" /kai/kai/config.toml
fi

TABLE=applications
SQL_EXISTS=$(printf '\dt "%s"' "$TABLE")
if [[ $(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "kai_db" -U $POSTGRES_USER -d $POSTGRES_DB -c "$SQL_EXISTS") ]]
then
    echo "load-data has run already"
else
  echo "load-data has not run yet, starting ..."
  echo "Fetching examples"
  if [ "$USE_HUB_IMPORTER" = "True" ]
  then
      cd /kai
      python ./kai/hub_importer.py --loglevel ${LOGLEVEL} --config_filepath ./kai/config.toml ${IMPORTER_ARGS} ${HUB_URL}
  else
      cd /kai/samples
      ./fetch_apps.py
      cd /kai
      python ./kai/service/incident_store/psql.py --config_filepath ./kai/config.toml --drop_tables False
  fi
fi

PYTHONPATH="/kai/kai" exec gunicorn --timeout 3600 -w $NUM_WORKERS --bind 0.0.0.0:8080 --worker-class aiohttp.GunicornWebWorker 'kai.server:app()'
