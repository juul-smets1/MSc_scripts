#!/usr/bin/env bash
#SBATCH --job-name=Python_Extract_Global_Areas
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH --time=7-00:00:00
#SBATCH --output=logs/python_extract_%j.out
#SBATCH --error=logs/python_extract_%j.err

set -euo pipefail

echo "Job started at $(date)"
echo "Running on host: $(hostname)"
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}"

module purge

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate vic_env

echo "Using python: $(which python)"

python - <<'EOF'
import sys, pandas, xarray, dask
print("Runtime OK:", sys.executable)
EOF

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export NUMEXPR_NUM_THREADS=${SLURM_CPUS_PER_TASK}

python /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/extract_global_areas.py

echo "Job finished at $(date)"

