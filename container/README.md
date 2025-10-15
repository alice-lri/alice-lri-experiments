# Container Folder README

This folder contains all the necessary files and instructions to use the containerized environment for the project. Here is an overview of the contents:

- **container.def**: The Apptainer/Singularity definition file used to build the container image. It specifies the environment, dependencies, and setup steps required for the project.
- **apt_packages.txt**: A list of system packages to be installed inside the container using apt.
- **conda_env.yml**: The Conda environment specification file, listing all Python dependencies and environments to be created inside the container.
- **container.sif**: (Not included by default) The Apptainer/Singularity Image File (SIF) that you will generate or download by following the instructions below.

## How to Obtain the Container Image

The `container.sif` file is not included in this repository by default due to its large size. You have two options to obtain it:

### 1. Build the Container Locally

If you have Apptainer/Singularity installed on your local machine, you can build the container image yourself by running:

```bash
apptainer build container.sif container.def
```

After building, transfer the resulting `container.sif` file to this `container/` folder on your HPC cluster using `scp` or a similar file transfer tool.

### 2. Download the Pre-built Container

Alternatively, you can directly download the pre-built container image from the following link:

[https://nextcloud.citius.gal/s/alice_lri_container](https://nextcloud.citius.gal/s/alice_lri_container)

Place the downloaded `container.sif` file in this `container/` folder on your HPC cluster.

