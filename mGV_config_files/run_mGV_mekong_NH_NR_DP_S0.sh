#!/bin/bash
#SBATCH --job-name=mGV_NH_NR_DP_S0
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/mGV_NH_NR_DP_S0_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/mGV_NH_NR_DP_S0_%j.err

# Resources
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=06:00:00
#SBATCH --mem=32G

# GPU request
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint=nvidia

echo "======================================================"
echo "   Starting mGV run: NH_NR_DP_S0"
echo "   Hostname  : $(hostname)"
echo "   Start time: $(date)"
echo "======================================================"

# Go to the project directory
WORKDIR="/lustre/nobackup/WUR/ESG/smets008/mGV/"
echo "Changing directory to: $WORKDIR"
cd "$WORKDIR" || { echo "Directory not found!"; exit 1; }

# Load Julia
echo "Loading Julia module..."
module load Julia/1.11.6-linux-x86_64

# Print GPU info for debugging
echo "Checking GPU..."
nvidia-smi

echo "------------------------------------------------------"
echo "Running mGV model: julia --project=. run.jl mekong 2000 2019"
echo "------------------------------------------------------"

# Run the model through SLURM
srun julia --project=. run.jl mekong 2000 2019

echo "======================================================"
echo "   Finished at: $(date)"
echo "======================================================"

