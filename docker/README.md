# Docker cheatsheet


## Build.

`docker build -t plancha-workflow-image:latest -f ./docker/Dockerfile .`
`docker tag plancha-workflow-image:latest groderg/plancha-workflow-image:latest`
`docker push groderg/plancha-workflow-image:latest`

```bash
docker build -t plancha-workflow-image:latest -f ./docker/Dockerfile . && \
docker tag plancha-workflow-image:latest groderg/plancha-workflow-image:latest && \
docker push groderg/plancha-workflow-image:latest
```

## Run.

Command to just open container :
`docker run -it --rm plancha-workflow-image:latest bash`

Command to link volume with container :
`docker run -it --rm -v /home/bioeos/Documents/Bioeos/plancha-session:/home/seatizen/plancha plancha-workflow-image:latest bash`

If entrypoint is set, launch command without bash.

Command with session_name 
`docker run -it --rm --env session_name='20231205_REU-HERMITAGE_ASV-2_03' -v /home/bioeos/Documents/Bioeos/plancha-session:/home/seatizen/plancha plancha-workflow-image:latest bash`


## Inside cmd

`python workflow.py -pcn /home/seatizen/plancha/20231205_REU-HERMITAGE_ASV-2_03/METADATA/prog_config.json -rp /home/seatizen/plancha`


# Singularity cheatsheet

Datarmor, the ifremer supercomputer, doesn't handle custom docker image easily. You need to convert your docker image to a singularity container.

## Build container.

`singularity build -f workflow.sif docker://groderg/plancha-workflow-image:latest`
`singularity build -f --sandbox workflow.sif docker://groderg/plancha-workflow-image:latest`

## Launch container.

`singularity run --env session_name=20240405_REU-TESSIER_ASV-1_01 --bind /home1/datawork/villien/plancha-session:/home/seatizen/plancha workflow.sif`