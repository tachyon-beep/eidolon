from airflow import DAG
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG(
    dag_id="hello_eidolon",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    schedule=None,
):
    EmptyOperator(task_id="noop")
