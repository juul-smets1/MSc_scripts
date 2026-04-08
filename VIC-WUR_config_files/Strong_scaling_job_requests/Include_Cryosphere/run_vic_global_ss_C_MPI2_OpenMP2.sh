#!/bin/bash
#SBATCH --job-name=VIC_Cryosphere_Strong_Scaling_Experiment
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/Include_Cryosphere/logs/VIC_Global_ss_C_MPI2_OpenMP2_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/Include_Cryosphere/logs/VIC_Global_ss_C_MPI2_OpenMP2_%j.err

# Resources
#SBATCH --partition=main
#SBATCH --nodelist=node[201-272]
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=2
#SBATCH --time=10-00:00:00
#SBATCH --mem=1000G

# ntasks = MPI ranks
# cpus-per-task = OpenMP threads
# mem=1000G to try and max out the nodes, the full 1024G did not work as SLURM request
# Different node selection has been made due to unavailable nodes in the original range node[201-272]

echo "Starting VIC Global run: Strong Scale Experiment"
echo "Running on host: $(hostname)"
echo "Time: $(date)"
echo "------------------------------------------------"

# Load required modules
ml 2024
ml OpenMPI/5.0.3-GCC-13.3.0
ml netCDF/4.9.2-gompi-2024a
ml GCC/13.3.0

# Set OpenMP threading for VIC
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
echo "Using $OMP_NUM_THREADS threads."

# Ensure logs directory exists
LOGDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/Include_Cryosphere/logs"
mkdir -p "$LOGDIR"

# Change to working directory
cd /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/Include_Cryosphere || {
  echo "Failed to cd to config directory"; exit 1
}

# Path to VIC executable
VIC_EXE="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/vic_image.exe"

# Path to configuration file
CONFIG="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/Include_Cryosphere/vic_global_ss_C_MPI2_OpenMP2_config.txt"

# Check that VIC exists and is executable
if [[ ! -x "$VIC_EXE" ]]; then
  echo "ERROR: VIC executable not found or not executable: $VIC_EXE"
  exit 2
fi

# Run VIC (MPI & OpenMP)
srun --mpi=pmix -n $SLURM_NTASKS "$VIC_EXE" -g "$CONFIG"

ret=$?
echo "--------------------------------------------------------------------"
echo "VIC Global Strong Scale Experimetn run finished with exit code: $ret"
echo "Time: $(date)"
exit $ret

