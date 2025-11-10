# Airflow Adapter Playground

Use this docker-compose stack to run a local Airflow instance that you can point the `airflow` adapter at.

```bash
cd docs/orchestrator/airflow
# Initialize metadata DB and admin user
AIRFLOW_UID=$(id -u) AIRFLOW_GID=0 docker compose up airflow-init
# Start webserver + scheduler
AIRFLOW_UID=$(id -u) AIRFLOW_GID=0 docker compose up -d airflow-webserver airflow-scheduler
# Check connectivity
./smoke_test.sh
```

The sample DAG `hello_eidolon` lives in `dags/hello_dag.py`. After Airflow is up, visit http://localhost:8080 (admin/admin) to trigger it. Configure the orchestrator pool entry with `adapter: airflow` to simulate dispatching tasks via the adapter stub.
