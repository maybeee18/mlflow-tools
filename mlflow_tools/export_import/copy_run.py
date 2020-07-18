""" 
Copies a run from one MLflow server to another.
"""

import time
import click
import mlflow
from mlflow_tools.export_import import utils
from mlflow_tools.export_import import BaseCopier, create_client, add_repr_to_MlflowClient
print("MLflow Version:", mlflow.version.VERSION)
print("MLflow Tracking URI:", mlflow.get_tracking_uri())

class RunCopier(BaseCopier):
    def __init__(self, src_client, dst_client, export_metadata_tags=False, use_src_user_id=False,  import_mlflow_tags=False):
        super().__init__(src_client, dst_client)
        self.export_metadata_tags = export_metadata_tags
        self.use_src_user_id = use_src_user_id
        self.import_mlflow_tags = import_mlflow_tags

    def copy_run(self, src_run_id, dst_exp_name):
        print("src_run_id:",src_run_id)
        dst_exp = self.get_experiment(self.dst_client,dst_exp_name)
        print("  dst_exp.name:",dst_exp.name)
        print("  dst_exp.id:",dst_exp.experiment_id)
        return self._copy_run(src_run_id, dst_exp.experiment_id)

    def _copy_run(self, src_run_id, dst_experiment_id):
        src_run = self.src_client.get_run(src_run_id)
        dst_run = self.dst_client.create_run(dst_experiment_id) # NOTE: does not set user_id; is 'unknown'
        self._copy_run_data(src_run, dst_run.info.run_id)
        local_path = self.src_client.download_artifacts(src_run_id,"")
        self.dst_client.log_artifacts(dst_run.info.run_id,local_path)
        self.dst_client.set_terminated(dst_run.info.run_id, src_run.info.status)
        return (dst_run.info.run_id, src_run.data.tags.get("mlflow.parentRunId",None))

    def _copy_run_data(self, src_run, dst_run_id):
        from mlflow.entities import Metric, Param, RunTag
        now = int(time.time()+.5)
        params = [ Param(k,v) for k,v in src_run.data.params.items() ]
        metrics = [ Metric(k,v,now,0) for k,v in src_run.data.metrics.items() ] # TODO: timestamp and step semantics?
        tags = utils.create_tags_for_metadata(self.src_client, src_run, self.export_metadata_tags)
        tags = utils.create_tags_for_mlflow_tags(tags, self.import_mlflow_tags) 
        utils.set_dst_user_id(tags, src_run.info.user_id, self.use_src_user_id)
        self.dst_client.log_batch(dst_run_id, metrics, params, tags)

@click.command()
@click.option("--src_uri", help="Source MLflow API URI", required=True, type=str)
@click.option("--dst_uri", help="Destination MLflow API URI", required=True, type=str)
@click.option("--src_run_id", help="Source run ID", required=True, type=str)
@click.option("--dst_experiment_name", help="Destination experiment name ", required=True, type=str)
@click.option("--export_metadata_tags", help="Export source run metadata tags", type=bool, required=False)
@click.option("--import_mlflow_tags", help="Import mlflow tags", type=bool, default=False)
@click.option("--use_src_user_id", help="Use source user ID", type=bool, default=False)

def main(src_uri, dst_uri, src_run_id, dst_experiment_name, export_metadata_tags, import_mlflow_tags, use_src_user_id):
    print("Options:")
    for k,v in locals().items():
        print(f"  {k}: {v}")
    src_client = create_client(src_uri)
    dst_client = create_client(dst_uri)
    print("src_client:",src_client)
    print("dst_client:",dst_client)
    src_client = create_client(src_uri)
    dst_client = create_client(dst_uri)
    print("  src_client:",src_client)
    print("  dst_client:",dst_client)
    copier = RunCopier(src_client, dst_client, export_metadata_tags, use_src_user_id, import_mlflow_tags)
    copier.copy_run(src_run_id, dst_experiment_name)

if __name__ == "__main__":
    main()
