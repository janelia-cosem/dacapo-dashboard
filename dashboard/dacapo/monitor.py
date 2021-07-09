from flask import render_template, request, jsonify
from dacapo.store.converter import converter

from dashboard.stores import get_stores
from .blue_print import bp
from .helpers import get_checklist_data
import dacapo

import itertools


@bp.route("/runs", methods=["GET", "POST"])
def get_runs():
    if request.method == "GET":
        context = get_checklist_data()
        return render_template("dacapo/runs.html", **context)
    if request.method == "POST":
        request_data = request.json
        run_component_ids = itertools.product(
            request_data["tasks"],
            request_data["datasets"],
            request_data["architectures"],
            request_data["trainers"],
        )

        config_store = get_stores().config
        runs = [
            {"id": run["id"],
                "execution_details": run["execution_details"],
                "task": config_store.retrieve_task_config(task),
                "dataset": config_store.retrieve_dataset_config(dataset),
                "architecture": config_store.retrieve_architecture_config(
                    architecture),
                "trainers": config_store.retrieve_trainer_config(trainer)
             }

            for task, dataset, architecture, trainer in run_component_ids
            if (run := config_store.retrieve_run_config(
                '_'.join([task, dataset, architecture, trainer])))
            is not None
        ]
        return jsonify(runs)

        # data = [
        #     {
        #         "name": run["hash"].split(":")[0],
        #         "repetition": run["repetition"],
        #         "trained_iterations": db.training_stats.find(
        #             {"run": run["id"]}
        #         ).count(),
        #         "started": datetime.fromtimestamp(run["started"])
        #         if run["started"] is not None
        #         else "NA",
        #         "task": run["task_config"],
        #         "data": "NA",
        #         "model": run["model_config"],
        #         "optimizer": run["optimizer_config"],
        #     }
        #     for run in db.runs.find({})
        # ]
        # raise NotImplementedError("Return json with runs filtered by post data")

    return render_template("dacapo/runs.html")


@ bp.route("/apply_config", methods=["GET"])
def apply_config():
    if request.method == "GET":
        return render_template("dacapo/apply_config.html")

    return render_template("dacapo/apply_config.html")


@ bp.route("/start_runs", methods=["POST"])
def start_runs():
    if request.method == "POST":
        config_json   =   request.json
        run_execution   =   converter.structure(
            config_json, dacapo.configs.RunExecution)
        run_configs   =   [
            dacapo.configs.Run(
                name=run["name"],
                task=run["task"][0],
                dataset=run["dataset"][0],
                architectures=run["architectures"][0],
                trainer=run["trainer"][0],
                execution_details=run_execution,
                repetition=i,
            )
            for run in config_json.pop("runs")
            for i in range(run_execution.repetitions)
        ]

        dacapo.run_all(run_configs, run_execution.num_workers)

    return jsonify({"success": True})
