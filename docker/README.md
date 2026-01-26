# Docker Environment for Learning

## Requirements

- Docker

## Usage

At the repo root folder, the following command build an image named `ece502c`:

```bash
docker build --progress=plain -t ece502c -f docker/Dockerfile .
```

Then, launch a container using the image. The container name is set to `ece502c_${USER}` (your username in the host system), using the image name `ece502c`. It also mounts the repo folder to `/workspace`

```bash
docker run -d --name ece502c_${USER} -v "$(pwd):/workspace" -w /workspace ece502c

```

Access the command line tool inside the container:

```bash
docker exec -it ece502c_${USER} bash
```

Now you are controlling the container (which is Ubuntu 24.04), and by default it starts from folder `/workspace` hosting files of this repo.