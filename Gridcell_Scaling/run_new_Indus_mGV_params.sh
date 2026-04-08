#!/usr/bin/env bash
#SBATCH --job-name=Create_Indus_mGV_Parameters
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=500G
#SBATCH --time=04:00:00
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Gridcell_Scaling/logs/new_Indus_mGV_params_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Gridcell_Scaling/logs/new_Indus_mGV_params_%j.err

set -euo pipefail
echo "Job started at $(date)"
echo "Running on host: $(hostname)"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}"

# Clean environment
module --force purge

# Activate conda (exact same as your Weak Scaling script)
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate vic_env
echo "Using python: $(which python)"
python --version
python -c "import xarray as xr, dask; print('xarray:', xr.__version__); print('dask:', dask.__version__)"

free -h
nproc

# Limit threading (exact same)
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export NUMEXPR_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export VECLIB_MAXIMUM_THREADS=${SLURM_CPUS_PER_TASK}

export DASK_DISTRIBUTED__WORKER__MEMORY__TARGET=0.8
export DASK_DISTRIBUTED__WORKER__MEMORY__SPILL=0.9
export DASK_DISTRIBUTED__WORKER__MEMORY__PAUSE=0.95

# Run the script
python new_Indus_mGV_params.py

echo "Job finished at $(date)"
