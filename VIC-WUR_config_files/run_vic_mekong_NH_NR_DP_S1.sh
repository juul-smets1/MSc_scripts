#!/bin/bash
#SBATCH --job-name=VIC_NH_NR_DP_S0
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/logs/VIC_NH_NR_DP_S1_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/logs/VIC_NH_NR_DP_S1_%j.err

# Resources
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=06:00:00
#SBATCH --mem=32G
#SBATCH --partition=main

echo "Starting VIC run: NH_NR_DP_S1"
echo "Running on host: $(hostname)"
echo "Time: $(date)"
echo "----------------------------------"

# Load required modules
ml 2024
ml OpenMPI/5.0.3-GCC-13.3.0
ml netCDF/4.9.2-gompi-2024a
ml GCC/13.3.0

# Ensure logs directory exists
LOGDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/logs"
mkdir -p "$LOGDIR"

# Change to working directory
cd /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files || {
  echo "Failed to cd to config directory"; exit 1
}

# Path to VIC executable
VIC_EXE="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/mekong/vic_image.exe"

# Path to configuration file
CONFIG="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/mekong/vic_mekong_config_NH_NR_DP_S1.txt"

# Check that VIC exists and is executable
if [[ ! -x "$VIC_EXE" ]]; then
  echo "ERROR: VIC executable not found or not executable: $VIC_EXE"
  exit 2
fi

# Run VIC
"$VIC_EXE" -g "$CONFIG"

ret=$?
echo "----------------------------------"
echo "VIC run finished with exit code: $ret"
echo "Time: $(date)"
exit $ret

