#!/usr/bin/env bash

# Start date that data will be generated from
date="2022-06-20"
num_days_to_generate=1

og_api_path="/root/dev/operationsgateway-api"
resources_path="${og_api_path}/util/realistic_data/resources"
schedule_file="schedule_calendar.yml"
channels_config="channels_config.yml"

output_dir="${og_api_path}/util/realistic_data/data"
s3_bucket="s3://og-directory-test/"

# Moving to the OG API directory so Poetry can be used to execute other scripts
cd $og_api_path

# Convert calendar schedule into format ready to be imported into MongoDB
poetry run python $og_api_path/util/realistic_data/calendar_conversion.py -r $resources_path -s $resources_path/schedule_calendar.yml -s $resources_path/daily_data_schedule.yml
# Upload files related to the data to Echo
poetry run s4cmd --endpoint-url https://s3.echo.stfc.ac.uk put $resources_path/ $s3_bucket --recursive --force

# Generate HDF files which are uploaded to Echo
for (( day=1; day<=$num_days_to_generate; day++ ))
do
    echo "Data to be generated for $date"
    poetry run epac-data-sim generator -s "${date}T00:00:00" -e "${date}T23:59:59" --schedule $resources_path/$schedule_file --channel-config $resources_path/$channels_config -o $output_dir -P

    # Put the data onto Echo and remove the data from local disk
    s3_start_time=`date +%s`
    poetry run s4cmd --endpoint-url https://s3.echo.stfc.ac.uk put $output_dir $s3_bucket --recursive --force
    s3_end_time=`date +%s`

    echo "Removing HDF files from disk"
    rm -f $output_dir/*.h5

    # Iterate the day ready for the next day of data to be generated
    date=$(date -I -d "$date + 1 day")
done

runtime=$((s3_end_time-s3_start_time))
echo "s4cmd put took $runtime seconds"
