#!/usr/bin/env bash

set -e
source /root/dev/simulated-data/simulated-data-310/bin/activate

# 1st June 2022 is a Wednesday, first experiement starts on the 6th
date="2022-06-21"
num_days_to_generate=1
schedule_file="resources/schedule_calendar.yml"
channels_config="resources/channels_config.yml"
output_dir="data"
# TODO - check if bucket has been created, create if not
s3_bucket="s3://og-realistic-data/"

# Convert calendar schedule into format ready to be imported into MongoDB
python calendar_conversion.py
# Upload files related to the data to Echo
s4cmd -n --endpoint-url https://s3.echo.stfc.ac.uk put resources/ $s3_bucket --recursive --force


# Generate HDF files which are uploaded to Echo
for (( day=1; day<=$num_days_to_generate; day++ ))
do
    echo "Data to be generated for $date"
    current_day_directory="${output_dir}/${date}/"
    mkdir -p $current_day_directory
    epac-data-sim generator -s "${date}T00:00:00" -e "${date}T23:59:59" --schedule $schedule_file --channel-config $channels_config -o $current_day_directory -P

    # Put the data onto Echo and remove the data from local disk
    s3_start_time=`date +%s`
    s4cmd -n --endpoint-url https://s3.echo.stfc.ac.uk put $current_day_directory $s3_bucket --recursive --force
    #/root/s5cmd --endpoint-url https://s3.echo.stfc.ac.uk cp $current_day_directory s3://og-realistic-data
    s3_end_time=`date +%s`

    echo "Removing $current_day_directory from disk"
    rm -rf $current_day_directory

    # Iterate the day ready for the next day of data to be generated
    date=$(date -I -d "$date + 1 day")

done

runtime=$((s3_end_time-s3_start_time))
echo "s4cmd put took $runtime seconds"

deactivate
