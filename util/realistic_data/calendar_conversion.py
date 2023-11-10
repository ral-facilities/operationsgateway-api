import argparse
from datetime import datetime, time

import yaml

# Dictionary counter to keep track of how many parts each experiment have
experiment_part_tracker = {}


def extract_experiment_metadata(experiment):
    part_counter = experiment_part_tracker.get(experiment["experiment_id"])
    if part_counter is None:
        experiment_part_tracker[experiment["experiment_id"]] = 1
    else:
        experiment_part_tracker[experiment["experiment_id"]] += 1

    part_number = experiment_part_tracker[experiment["experiment_id"]]
    start_date = datetime.combine(experiment["start"], time(0, 0, 0, 0))
    end_date = datetime.combine(experiment["stop"], time(23, 59, 59, 0, tzinfo=None))

    return {
        "end_date": {"$date": f"{end_date.isoformat(timespec='milliseconds')}Z"},
        "experiment_id": experiment["experiment_id"],
        "part": part_number,
        "start_date": {"$date": f"{start_date.isoformat(timespec='milliseconds')}Z"},
    }


def experiment_start_date(e):
    return e["start"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resource-directory", type=str, required=True)
    parser.add_argument(
        "-s",
        "--schedule-file",
        action="append",
        type=str,
        required=True,
    )

    args = parser.parse_args()
    resource_path = args.resource_directory
    schedule_files = args.schedule_file

    schedules = []
    for file_path in schedule_files:
        with open(file_path, encoding="utf-8") as calendar_file:
            schedules.append(yaml.safe_load(calendar_file))

    input_experiments = []
    for schedule in schedules:
        for experiment_areas in schedule.values():
            if isinstance(experiment_areas, list):
                input_experiments.extend(experiment_areas)

    # Sort experiments from YAML file so they're sorted by date rather than experiment
    # area - EA1 and EA2 have no relevance for our data
    input_experiments.sort(key=experiment_start_date)
    experiments = [
        extract_experiment_metadata(experiment) for experiment in input_experiments
    ]

    with open(f"{resource_path}/experiments_for_mongoimport.json", "w") as f:
        for experiment in experiments:
            f.write(str(experiment).replace("'", '"') + "\n")


if __name__ == "__main__":
    main()
