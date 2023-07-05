#!/usr/bin/env bash

date="2022-06-20"
num_days_to_generate=1

virtualenv_path="/root/dev/simulated-data/simulated-data-310/bin/activate"
og_api_path="/root/dev/operationsgateway-api"
resources_path="${og_api_path}/util/realistic_data/resources"
schedule_file="schedule_calendar.yml"
channels_config="channels_config.yml"

output_dir="${og_api_path}/util/realistic_data/data"
s3_bucket="s3://og-realistic-data/"

set -e
source $virtualenv_path

# Convert calendar schedule into format ready to be imported into MongoDB
python $og_api_path/util/realistic_data/calendar_conversion.py -r $resources_path
# Upload files related to the data to Echo
s4cmd --endpoint-url https://s3.echo.stfc.ac.uk put $resources_path/ $s3_bucket --recursive --force

# Generate HDF files which are uploaded to Echo
for (( day=1; day<=$num_days_to_generate; day++ ))
do
    echo "Data to be generated for $date"
    current_day_directory="${output_dir}/${date}/"
    mkdir -p $current_day_directory
    epac-data-sim generator -s "${date}T00:00:00" -e "${date}T23:59:59" --schedule $resources_path/$schedule_file --channel-config $resources_path/$channels_config -o $current_day_directory -P

    # Put the data onto Echo and remove the data from local disk
    s3_start_time=`date +%s`
    s4cmd --endpoint-url https://s3.echo.stfc.ac.uk put $current_day_directory $s3_bucket --recursive --force
    s3_end_time=`date +%s`

    echo "Removing $current_day_directory from disk"
    rm -rf $current_day_directory

    # Iterate the day ready for the next day of data to be generated
    date=$(date -I -d "$date + 1 day")
done

runtime=$((s3_end_time-s3_start_time))
echo "s4cmd put took $runtime seconds"

deactivate
