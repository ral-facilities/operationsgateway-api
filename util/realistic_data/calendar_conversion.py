import argparse
from datetime import datetime, time

import yaml


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


def experiment_start_date(e):
    return e["start_date"]["$date"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--resource-directory", type=str, required=True)
    parser.add_argument("-s", "--schedule-file", action="append", type=str, required=True)

    args = parser.parse_args()
    resource_path = args.resource_directory
    schedule_files = args.schedule_file

    schedules = []
    for file_path in schedule_files:
        with open(file_path, encoding="utf-8") as calendar_file:
            schedules.append(yaml.safe_load(calendar_file))

    experiments = []
    for schedule in schedules:
        for experiment_areas in schedule.values():
            # Searching for the experiment areas that will contain experiments
            if isinstance(experiment_areas, list):
                experiments.extend(
                    [
                        extract_experiment_metadata(experiment)
                        for experiment in experiment_areas
                    ],
                )

    # The ordering of experiments in the database has no impact to functionality but
    # helps readability for anyone trying to debug with this data
    experiments.sort(key=experiment_start_date)

    with open(f"{resource_path}/experiments_for_mongoimport.json", "w") as f:
        for experiment in experiments:
            f.write(str(experiment).replace("'", '"') + "\n")


if __name__ == "__main__":
    main()
