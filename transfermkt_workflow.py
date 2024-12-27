from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime
from airflow.hooks.base import BaseHook

# Fetch AWS credentials from Airflow connection
aws_conn = BaseHook.get_connection('aws_default')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
}

with DAG(
    'transfermkt_workflow',
    default_args=default_args,
    description='Run TransferMkt scripts in Docker containers',
    schedule_interval='0 14 * * 6',  # Every Saturday at 2:00 PM
    start_date=datetime(2024, 12, 6),
    catchup=False,
) as dag:

    # Task 1: Run transfer_mkt_players.py
    run_players_script = DockerOperator(
        task_id='run_players_script',
        image='transfermkt_app:latest',
        command="python /app/transfer_mkt_players.py",
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,
        mount_tmp_dir=False,  # Prevent temporary directory mount warnings
	force_pull=True,
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
#            'AWS_DEFAULT_REGION': 'us-east-1',
        },
    )

    # Task 2: Run transfer_mkt_transform.py
    run_transform_script = DockerOperator(
        task_id='run_transform_script',
        image='transfermkt_app:latest',
        command="python /app/transfer_mkt_transform.py",
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge',
        auto_remove=True,
        mount_tmp_dir=False,  # Prevent temporary directory mount warnings
	force_pull=True,
        environment={
            'AWS_ACCESS_KEY_ID': aws_conn.login,
            'AWS_SECRET_ACCESS_KEY': aws_conn.password,
#            'AWS_DEFAULT_REGION': 'us-east-1',
        },
    )

    # Define task dependencies
    run_players_script >> run_transform_script
