#!/bin/sh

cd /home/seatizen/app

# Check for environment variable and set command accordingly
if [ ! -d "/home/seatizen/plancha/$session_name" ]; then
  echo "/home/seatizen/plancha/$session_name doesn't exist."
else
    COMMAND="python workflow.py -pcn /home/seatizen/plancha/$session_name/METADATA/prog_config.json -rp /home/seatizen/plancha"

    # Execute the command
    exec $COMMAND
fi
