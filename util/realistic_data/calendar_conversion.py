from datetime import datetime, time

import yaml


with open("resources/schedule_calendar.yml", encoding="utf-8") as calendar_file:
    schedule = yaml.safe_load(calendar_file)


def extract_experiment_metadata(experiment):
    # As EPAC-DataSim doesn't have the concept of multi-part experiments, we're setting
    # every experiment to be part 1
    part_number = 1
    start_date = datetime.combine(experiment["start"], time(23, 59, 59, 0))
    end_date = datetime.combine(experiment["stop"], time(0, 0, 0, 0, tzinfo=None))

    return {
        "_id": f"{experiment['experiment_id']}-{part_number}",
        "end_date": {"$date": f"{end_date.isoformat(timespec='milliseconds')}Z"},
        "experiment_id": experiment["experiment_id"],
        "part": part_number,
        "start_date": {"$date": f"{start_date.isoformat(timespec='milliseconds')}Z"},
    }


experiments = []
for experiment_areas in schedule.values():
    # Searching for the experiment areas that will contain experiments
    if isinstance(experiment_areas, list):
        experiments.extend(
            [
                extract_experiment_metadata(experiment)
                for experiment in experiment_areas
            ],
        )


def experiment_start_date(e):
    return e["start_date"]["$date"]


# The ordering of experiments in the database has no impact to functionality but helps
# readability for anyone trying to debug with this data
experiments.sort(key=experiment_start_date)

with open("resources/experiments_for_mongoimport.json", "w") as f:
    for experiment in experiments:
        f.write(str(experiment).replace("'", '"') + "\n")
