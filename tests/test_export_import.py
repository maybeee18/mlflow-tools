import mlflow
import os, shutil
from utils_test import create_experiment, compare_dirs
from mlflow_tools.tools.dump_run import dump_run

from mlflow_tools.export_import.export_run import RunExporter
from mlflow_tools.export_import.import_run import RunImporter
from mlflow_tools.export_import.import_run import RunImporter
from mlflow_tools.export_import.export_experiment import ExperimentExporter
from mlflow_tools.export_import.import_experiment import ExperimentImporter
from mlflow_tools.export_import.copy_run import RunCopier
from mlflow_tools.export_import.copy_experiment import ExperimentCopier

client = mlflow.tracking.MlflowClient()
output = "out"

def create_simple_run():
    exp = create_experiment()
    with mlflow.start_run(run_name="my_run") as run:
        mlflow.log_param("p1","0.1")
        mlflow.log_metric("m1", 0.1)
        mlflow.set_tag("my_tag","my_val")
        with open("info.txt", "w") as f:
            f.write("Hi artifact")
        mlflow.log_artifact("info.txt")
        mlflow.log_artifact("info.txt","dir2")
    return exp,run

def init_output_dir():
    if os.path.exists(output):
        shutil.rmtree(output)
    os.makedirs(output)
    os.makedirs(os.path.join(output,"run1"))
    os.makedirs(os.path.join(output,"run2"))

def dump_runs(run1, run2):
    #print("run1:",run1)
    #print("run2:",run2)
    print("======= Run1")
    dump_run(run1)
    print("======= Run2")
    dump_run(run2)

# == Export/import Run tests

def init_run_test(exporter, importer, verbose=False):
    init_output_dir()
    exp, run = create_simple_run()
    exporter.export_run(run.info.run_id, output)

    experiment_name = f"{exp.name}_import" 
    res = importer.import_run(experiment_name, output)
    if verbose: print("res:",res)

    run1 = client.get_run(run.info.run_id)
    run2 = client.get_run(res[0])
    if verbose: dump_runs(run1, run2)
    return run1, run2

def test_run_basic():
    run1, run2 = init_run_test(RunExporter(), RunImporter())
    compare_runs(run1, run2)

def test_run_no_import_mlflow_tags():
    run1, run2 = init_run_test(RunExporter(), RunImporter(import_mlflow_tags=False))
    compare_run_no_import_mlflow_tags(run1, run2)

def test_run_import_metadata_tags():
    run1, run2 = init_run_test(RunExporter(export_metadata_tags=True), RunImporter(import_metadata_tags=True), verbose=False)
    compare_run_import_metadata_tags(run1, run2)

# == Export/import Experiment tests

def init_exp_test(exporter, importer, verbose=False):
    init_output_dir()
    exp, run = create_simple_run()
    run1 = client.get_run(run.info.run_id)
    exporter.export_experiment(exp.name, output)

    experiment_name = f"{exp.name}_import"
    importer.import_experiment(experiment_name, output)
    exp2 = client.get_experiment_by_name(experiment_name)
    infos = client.list_run_infos(exp2.experiment_id)
    run2 = client.get_run(infos[0].run_id)

    if verbose: dump_runs(run1, run2)
    return run1, run2

def test_exp_basic():
    run1, run2 = init_exp_test(ExperimentExporter(), ExperimentImporter(), True)
    compare_runs(run1, run2)

def test_exp_no_import_mlflow_tags():
    run1, run2 = init_exp_test(ExperimentExporter(), ExperimentImporter(import_mlflow_tags=False))
    compare_run_no_import_mlflow_tags(run1, run2)

def test_exp_import_metadata_tags():
    run1, run2 = init_exp_test(ExperimentExporter(export_metadata_tags=True), ExperimentImporter(import_metadata_tags=True), verbose=False)
    compare_run_import_metadata_tags(run1, run2)

# == Copy run tests

def init_run_copy_test(copier, verbose=False):
    init_output_dir()
    exp, run = create_simple_run()
    run1 = client.get_run(run.info.run_id)
    dst_experiment_name = f"{exp.name}_copy_run"
    copier.copy_run(run1.info.run_id, dst_experiment_name)
    exp2 = client.get_experiment_by_name(dst_experiment_name)
    infos = client.list_run_infos(exp2.experiment_id)
    run2 = client.get_run(infos[0].run_id)
    if verbose: dump_runs(run1, run2)
    return run1, run2

def test_copy_run_basic():
    run1, run2 = init_run_copy_test(RunCopier(client, client), verbose=False)
    compare_runs(run1, run2)

def test_copy_run_import_metadata_tags():
    run1, run2 = init_run_copy_test(RunCopier(client, client, export_metadata_tags=True))
    compare_run_import_metadata_tags(run1, run2)

# == Copy experiment tests

def init_exp_copy_test(copier, verbose=False):
    init_output_dir()
    exp, run = create_simple_run()
    run1 = client.get_run(run.info.run_id)
    dst_experiment_name = f"{exp.name}_copy_exp"

    copier.copy_experiment(exp.name, dst_experiment_name)
    exp2 = client.get_experiment_by_name(dst_experiment_name)
    infos = client.list_run_infos(exp2.experiment_id)
    run2 = client.get_run(infos[0].run_id)
    if verbose: dump_runs(run1, run2)
    return run1, run2

def test_copy_exp_basic():
    run1, run2 = init_exp_copy_test(ExperimentCopier(client, client), verbose=False)
    compare_runs(run1, run2)

def test_copy_exp_import_metadata_tags():
    run1, run2 = init_exp_copy_test(ExperimentCopier(client, client, export_metadata_tags=True))
    compare_run_import_metadata_tags(run1, run2)

# == Compare runs

def compare_run_no_import_mlflow_tags(run1, run2):
    compare_runs_no_tags(run1, run2)
    assert "mlflow.runName" in run1.data.tags
    assert not "mlflow.runName" in run2.data.tags
    run1.data.tags.pop("mlflow.runName")
    assert run1.data.tags == run2.data.tags

def compare_run_import_metadata_tags(run1, run2):
    compare_runs_no_tags(run1, run2)
    metadata_tags = { k:v for k,v in run2.data.tags.items() if k.startswith("mlflow_tools.metadata") }
    assert len(metadata_tags) > 0
    #metadata_tags = { k.replace("mlflow_tools.metadata.",""):v for k,v in run2.data.tags.items() if k.startswith("mlflow_tools.metadata") }
    #assert run1.data.tags == metadata_tags

def compare_runs_no_tags(run1, run2):
    assert run1.info.lifecycle_stage == run2.info.lifecycle_stage
    assert run1.info.status == run2.info.status
    assert run1.data.params == run2.data.params
    assert run1.data.metrics == run2.data.metrics
    path1 = client.download_artifacts(run1.info.run_id, ".", dst_path=os.path.join(output,"run1"))
    path2 = client.download_artifacts(run2.info.run_id, ".", dst_path=os.path.join(output,"run2"))
    assert compare_dirs(path1,path2)

def compare_runs(run1, run2):
    compare_runs_no_tags(run1, run2)
    assert run1.data.tags == run2.data.tags

