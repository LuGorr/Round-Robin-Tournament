# CDMO


## Using Docker
First, execute
```sh
 docker build -t CDMO .
```
to assemble the image for the project.

Then run
```sh
docker run -v ./res:/res CDMO
```
to start the Docker container with the mounted directories.