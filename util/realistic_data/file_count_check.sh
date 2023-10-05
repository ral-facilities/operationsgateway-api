start_date="2022-10-10"
end_date="2022-10-23"

num_days_to_check="$((($(date -d $end_date +%s) - $(date -d $start_date +%s))/86400))"
date=$start_date

for (( day=1; day<=$num_days_to_check; day++ ))
do
    num_files="$(poetry run s4cmd --endpoint-url https://s3.echo.stfc.ac.uk ls "s3://OG-YEAR-OF-SIMULATED-DATA/data/${date}*" | wc -l)"
    echo $date: $num_files
    date=$(date -I -d "$date + 1 day")
done
