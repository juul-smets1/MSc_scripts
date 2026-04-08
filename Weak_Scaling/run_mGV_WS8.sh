#!/bin/bash
#SBATCH --job-name=mGV_WS8
#SBATCH --partition=gpu
#SBATCH --nodelist=gpun200,gpun[201-203]
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --mem=500G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=00:10:00
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Weak_Scaling/logs/mGV_WS8_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/Weak_Scaling/logs/mGV_WS8_%j.err

echo "=================================================================================="
echo "   Starting mGV run: zarr output implementation gitbranch for mGV Weak Scaling 8"
echo "   Hostname  : $(hostname)"
echo "   Start time: $(date)"
echo "=================================================================================="

# Go to the project directory
WORKDIR="/lustre/nobackup/WUR/ESG/smets008/VRAM_zarr_mGV"
echo "Changing directory to: $WORKDIR"
cd "$WORKDIR" || { echo "Directory not found!"; exit 1; }

# Load Julia
echo "Loading Julia module..."
module load 2023
module load Julia/1.11.3-linux-x86_64
module load GPU

# Print GPU info for debugging
echo "Checking GPU..."
nvidia-smi

echo "---------------------------------------------------------------"
echo "Ensuring Julia packages are installed..."
julia --project=. -e 'using Pkg; Pkg.instantiate()'

echo "------------------------------------------------------------------"
echo "Running mGV model: julia --project=. run.jl WS 1990 - 1994" --nc
echo "------------------------------------------------------------------"

# Run the model through SLURM
julia -t $SLURM_CPUS_PER_TASK --project=. run.jl global 1990 1994 --nc

echo "======================================================"
echo "   Finished at: $(date)"
echo "======================================================"

