#!/bin/bash
#SBATCH --job-name=VIC_RAM_TEST
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/logs/VIC_Global_RAM_MPI64_OpenMP2_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/logs/VIC_Global_RAM_MPI64_OpenMP2_%j.err

# Resources
#SBATCH --partition=main
#SBATCH --nodelist=node[201-272]
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=2
#SBATCH --time=5-00:00:00
#SBATCH --mem=1000G

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
LOGDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/logs"
mkdir -p "$LOGDIR"

# ==========================
# Monitoring setup
# ==========================
LOGFILE="$LOGDIR/VIC-WUR_RAM_FLOPS.csv"

# Estimate peak FLOPS per core (AVX512, double precision)
PEAK_FLOPS_PER_CORE=31.25  # GFLOPS per core
TOTAL_CORES=$(($SLURM_NTASKS * $SLURM_CPUS_PER_TASK))
PEAK_FLOPS=$(echo "$PEAK_FLOPS_PER_CORE * $TOTAL_CORES" | bc -l)  # Total peak GFLOPS

# CSV header
echo "timestamp,CPU_RAM_used_MB,CPU_RAM_free_MB,CPU_utilization_percent,Moving_Avg_FLOPS_GFLOPS,Total_FLOPS_executed_GFLOPS" > $LOGFILE

# Initialize total FLOPS
TOTAL_FLOPS=0

# Function to compute moving average
MOVING_WINDOW=5  # seconds
declare -a FLOPS_BUFFER

monitor_resources() {
    while true; do
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

        # RAM
        read RAM_USED RAM_FREE <<< $(free -m | awk '/Mem:/ {print $3, $4}')

        # CPU utilization across all cores (top's idle column)
        CPU_UTIL=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}')

        # Instant FLOPS based on CPU utilization
        INST_FLOPS=$(echo "$PEAK_FLOPS * $CPU_UTIL / 100" | bc -l)

        # Update moving average buffer
        FLOPS_BUFFER+=($INST_FLOPS)
        if [ ${#FLOPS_BUFFER[@]} -gt $MOVING_WINDOW ]; then
            FLOPS_BUFFER=("${FLOPS_BUFFER[@]:1}")  # drop oldest
        fi

        # Compute moving average
        SUM=0
        for val in "${FLOPS_BUFFER[@]}"; do
            SUM=$(echo "$SUM + $val" | bc -l)
        done
        MOVING_AVG=$(echo "$SUM / ${#FLOPS_BUFFER[@]}" | bc -l)

        # Update total FLOPS (approximation: add 1 second worth of moving average)
        TOTAL_FLOPS=$(echo "$TOTAL_FLOPS + $MOVING_AVG" | bc -l)

        # Write to CSV
        echo "$TIMESTAMP,$RAM_USED,$RAM_FREE,$CPU_UTIL,$MOVING_AVG,$TOTAL_FLOPS" >> $LOGFILE

        sleep 1
    done
}

# Start monitoring in background
monitor_resources &
MONITOR_PID=$!

# Change to working directory
cd /lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests || {
  echo "Failed to cd to config directory"; exit 1
}

# Path to VIC executable
VIC_EXE="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/vic_image.exe"

# Path to configuration file
CONFIG="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/vic_global_ss_config.txt"

# Check that VIC exists and is executable
if [[ ! -x "$VIC_EXE" ]]; then
  echo "ERROR: VIC executable not found or not executable: $VIC_EXE"
  exit 2
fi

# Run VIC (MPI & OpenMP)
srun --mpi=pmix -n $SLURM_NTASKS "$VIC_EXE" -g "$CONFIG"

RET=$?

# Stop monitoring
kill $MONITOR_PID

echo "--------------------------------------------------------------------"
echo "VIC Global Strong Scale Experiment run finished with exit code: $RET"
echo "Time: $(date)"
exit $RET
