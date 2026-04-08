#!/usr/bin/env bash
#SBATCH --job-name=Python_Extract_InSitu
#SBATCH --partition=main
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/python_extract_in_situ_%j.out
#SBATCH --error=logs/python_extract_in_situ_%j.err

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

# ---- Limit threading
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export NUMEXPR_NUM_THREADS=${SLURM_CPUS_PER_TASK}
export VECLIB_MAXIMUM_THREADS=${SLURM_CPUS_PER_TASK}

# ---- Run extraction
python /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/extract_in_situ.py

echo "Job finished at $(date)"

