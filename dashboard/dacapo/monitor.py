from flask import render_template, request, jsonify
from dacapo.experiments import RunConfig

from dashboard.stores import get_stores
from .blue_print import bp
from .helpers import get_checklist_data, get_evaluator_score_names
from dacapo import train

import itertools

from dacapo.plot import plot_runs


@bp.route('/plot', methods=["POST"])
def plot():
    if request.method == "POST":
        plot_info = request.json
        return plot_runs(plot_info["runs"],
                         validation_scores=plot_info["scoreNames"],
                         higher_is_betters=plot_info["higherIsBetters"],
                         plot_losses=plot_info["plotLosses"],
                         return_json=True)


@bp.route("/runs", methods=["GET", "POST"])
def get_runs():
    if request.method == "GET":
        context = get_checklist_data()
        return render_template("dacapo/runs.html", **context)
    if request.method == "POST":
        request_data = request.json
        run_component_ids = itertools.product(
            request_data["tasks"],
            request_data["datasplits"],
            request_data["architectures"],
            request_data["trainers"],
        )

        config_store = get_stores().config
        run_config_names = config_store.retrieve_run_config_names()
        run_config_basenames = [n.split(":")[0] for n in run_config_names]
        runs = [
            {
                "name": '_'.join([task, datasplit, architecture, trainer]),
                "task_config_name": task,
                "datasplit_config_name": datasplit,
                "architecture_config_name": architecture,
                "trainer_config_name": trainer,
                "evaluator_score_names": get_evaluator_score_names(task)
            }
            for task, datasplit, architecture, trainer in run_component_ids
            if '_'.join([task, datasplit, architecture, trainer])
            in run_config_basenames
        ]
        return jsonify(runs)

    return render_template("dacapo/runs.html")


@bp.route("/apply_config", methods=["GET"])
def apply_config():
    if request.method == "GET":
        return render_template("dacapo/apply_config.html")

    return render_template("dacapo/apply_config.html")


@bp.route("/start_runs", methods=["POST"])
def start_runs():
    if request.method == "POST":
        config_json = request.json
        config_store = get_stores().config
        for run in config_json.pop("runs"):
            for i in range(int(config_json["repetitions"])):
                run_config_name = ("_").join([run["task_config_name"],
                                             run["datasplit_config_name"],
                                             run["architecture_config_name"],
                                             run["trainer_config_name"]])+f":{i}"

                run_config = RunConfig(
                    name=run_config_name,
                    task_config=config_store.retrieve_task_config(
                        run["task_config_name"]),
                    architecture_config=config_store.retrieve_architecture_config(
                        run["architecture_config_name"]),
                    trainer_config=config_store.retrieve_trainer_config(
                        run["trainer_config_name"]),
                    datasplit_config=config_store.retrieve_datasplit_config(
                        run["datasplit_config_name"]),
                    repetition=1,
                    num_iterations=int(config_json["num_iterations"]),
                    snapshot_interval=int(config_json["snapshot_interval"]),
                    validation_score='blipp_score',
                    validation_score_minimize=False
                )
                config_store.store_run_config(run_config)
                train(run_config_name)

    return jsonify({"success": True})
