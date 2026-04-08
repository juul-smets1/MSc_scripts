#!/usr/bin/env bash
#SBATCH --job-name=Python_Extract_Global_Valid
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=3-00:00:00
#SBATCH --output=logs/python_extract_valid_%j.out
#SBATCH --error=logs/python_extract_valid_%j.err

set -euo pipefail

echo "Job started at $(date)"
echo "Running on host: $(hostname)"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}"

# ---- Clean environment
module --force purge

# ---- Conda
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate vic_env

echo "Using python: $(which python)"

python - <<'EOF'
import sys, xarray, dask, numpy
print("Runtime OK:", sys.executable)
EOF

# ---- CRITICAL: limit thread usage
export OMP_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export MKL_NUM_THREADS=8
export NUMEXPR_NUM_THREADS=8
export VECLIB_MAXIMUM_THREADS=8

# ---- Optional: safer Dask defaults
export DASK_DISTRIBUTED__WORKER__MEMORY__TARGET=0.8
export DASK_DISTRIBUTED__WORKER__MEMORY__SPILL=0.9
export DASK_DISTRIBUTED__WORKER__MEMORY__PAUSE=0.95

# ---- Run
python /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/extract_global_valid.py

echo "Job finished at $(date)"

