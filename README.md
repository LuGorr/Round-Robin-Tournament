# CDMO


## Using Docker
First, execute
```sh
 docker build -t cdmo_chagoko .
```
to assemble the image for the project.

Then run
```sh
docker run --mount src="${pwd}"/res,target=/app/res,type=bind cdmo_chagoko
```
to start the Docker container with the mounted directories.