# ALICE-LRI Experiments

This repository contains all the code, scripts, and configuration required to reproduce the experiments for the ALICE-LRI paper. It is designed to provide a fully reproducible workflow, from data preparation to results and paper figures.

## Reproducibility Guide

The complete step-by-step process to reproduce all experiments and results is described in detail in [REPRODUCIBILITY.md](./REPRODUCIBILITY.md).

## Repository Structure

- **alice-lri/**: Submodule containing the ALICE-LRI library (core algorithm, C++/Python bindings).
- **rtst-modified/**: Fork of the original RTST compression algorithm, including both the original and modified versions for evaluation.
- **container/**: Container definition and environment files for reproducible builds (Apptainer/Singularity).
- **results/**: Databases, CSVs, and generated figures/tables from experiments.
- **scripts/**: Automation scripts for data preparation, experiment execution, and analysis.
- **.env**: Environment configuration file. This file defines important paths and variables for both local and HPC environments.

## Related Repositories and Organization

- [ALICE-LRI GitHub Organization](https://github.com/alice-lri): The main organization hosting the ALICE-LRI ecosystem and related projects.

- [ALICE-LRI (core library)](https://github.com/alice-lri/alice-lri): The main repository for the ALICE-LRI library. This is included here as the `alice-lri/` subfolder.

- [RTST-Modified](https://github.com/alice-lri/rtst-modified): Fork of the original [RTST compression algorithm](https://github.com/horizon-research/Real-Time-Spatio-Temporal-LiDAR-Point-Cloud-Compression), containing both the original and modified versions for evaluation. Included here as the `rtst-modified/` subfolder.

## Paper and Citation

The ALICE-LRI algorithm and experiments are described in our paper:

> **Title:** _ALICE-LRI: A General Method for Lossless Range Image Generation for Spinning LiDAR Sensors without Calibration Metadata_  
> **Authors:** _Samuel Soutullo, Miguel Yermo, David L. Vilariño, Óscar G. Lorenzo, José C. Cabaleiro, Francisco F. Rivera_  
> **Link:** _TODO: Add link when available_

**How to cite:**
```bibtex
TODO: Add BibTeX citation
```

---

For questions or issues, please refer to [REPRODUCIBILITY.md](./REPRODUCIBILITY.md) or contact the corresponding author of the paper (Samuel Soutullo).
