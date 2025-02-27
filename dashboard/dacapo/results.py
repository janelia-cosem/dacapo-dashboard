from flask import render_template, request, jsonify

from dashboard.db import get_db
from .blue_print import bp
from .helpers import get_checklist_data

from datetime import datetime


@bp.route("/results", methods=["GET", "POST"])
def get_results():
    if request.method == "GET":
        db = get_db()
        context = get_checklist_data()
        context.update(
            {
                "scores": set(
                    [
                        key
                        for run in db.runs.find({})
                        for validation_score in db.validation_scores.find(
                            {"run": run["id"]}
                        ).limit(1)
                        for key in validation_score["parameter_scores"]["0"]["scores"][
                            "sample"
                        ].keys()
                    ]
                ),
            }
        )
        return render_template("dacapo/results.html", **context)
    elif request.method == "POST":
        db = get_db()
        request_data = request.json
        runs = [
            {
                "name": run["hash"].split(":")[0],
                "repetition": run["repetition"],
                "trained_iterations": db.training_stats.find(
                    {"run": run["id"]}
                ).count(),
                "started": datetime.fromtimestamp(run["started"])
                if run["started"] is not None
                else "NA",
                "task": run["task_config"],
                "data": "NA",
                "model": run["model_config"],
                "optimizer": run["optimizer_config"],
            }
            for run in db.runs.find(
                {"task_config": {"$in": [x.strip() for x in request_data["tasks"]]}}
            )
        ]
        return jsonify(runs)

    return render_template("dacapo/results.html")
