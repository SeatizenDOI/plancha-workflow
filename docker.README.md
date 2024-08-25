# Docker cheatsheet


## Build.

`docker build -t plancha-workflow-image:latest .`
`docker tag plancha-workflow-image:latest groderg/plancha-workflow-image:latest`
`docker push groderg/plancha-workflow-image:latest`

```bash
docker build -t plancha-workflow-image:latest -f . && \
docker tag plancha-workflow-image:latest groderg/plancha-workflow-image:latest && \
docker push groderg/plancha-workflow-image:latest
```

## Run.

Command to just open container :
`docker run --rm plancha-workflow-image:latest bash`

Command to link volume with container :
`docker run --rm -v /home/bioeos/Documents/Bioeos/plancha-session:/home/seatizen/plancha plancha-workflow-image:latest bash`
`docker run -v /home/bioeos/Documents/Ifremer/plancha:/home/seatizen/plancha plancha-workflow-image:latest`

If entrypoint is set, launch command without bash.

Command with session_name 
`docker run --rm -v /home/bioeos/Documents/Bioeos/plancha-session:/home/seatizen/plancha plancha-workflow-image:latest [OPTIONS WORKFLOW.PY]`


# Singularity cheatsheet

Datarmor, the ifremer supercomputer, doesn't handle custom docker image easily. You need to convert your docker image to a singularity container.

## Build container.

`singularity build -f workflow.sif docker://groderg/plancha-workflow-image:latest`
`singularity build -f --sandbox workflow.sif docker://groderg/plancha-workflow-image:latest`

## Launch container.

`singularity run --bind /home1/datawork/villien/plancha-session:/home/seatizen/plancha workflow.sif`