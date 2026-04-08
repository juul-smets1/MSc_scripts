#!/bin/bash
#SBATCH --job-name=mGV_Global_VRAM_RAM
#SBATCH --partition=gpu
#SBATCH --nodelist=gpun200,gpun[201-203]
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --mem=500G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=05:00:00
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/mGV_Global_VRAM_RAM_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/mGV_Global_VRAM_RAM_%j.err

set -euo pipefail

echo "=================================================================================="
echo "   Starting mGV run: zarr output implementation gitbranch Global_VRAM_RAM"
echo "   Hostname  : $(hostname)"
echo "   Start time: $(date)"
echo "=================================================================================="

WORKDIR="/lustre/nobackup/WUR/ESG/smets008/VRAM_zarr_mGV"
cd "$WORKDIR" || { echo "Directory not found!"; exit 1; }

module purge
module load 2023
module load Julia/1.11.3-linux-x86_64
module load GPU

nvidia-smi

julia --project=. -e 'using Pkg; Pkg.instantiate()'

LOGDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs"
LOGFILE="${LOGDIR}/mGV_VRAM_RAM_FLOPS_${SLURM_JOB_ID}.csv"
SUMMARYFILE="${LOGDIR}/mGV_TOTAL_FLOPS_${SLURM_JOB_ID}.txt"

PEAK_FLOPS=19500
WINDOW=30
SAMPLE_INTERVAL=0.2
LOG_INTERVAL=1

mkdir -p "$LOGDIR"

echo "timestamp,CPU_RAM_used_MiB,CPU_RAM_free_MiB,GPU_used_MiB,GPU_free_MiB,GPU_total_MiB,GPU_util_percent,Instant_GFLOPS,MovingAvg_GFLOPS" > "$LOGFILE"

GPU_TOTAL=$(nvidia-smi --id=0 --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | tr -d ' ' || echo 0)
echo "GPU total memory detected: ${GPU_TOTAL} MiB"

monitor_resources() {

    declare -a FLOP_WINDOW
    for ((i=0;i<WINDOW;i++)); do
        FLOP_WINDOW[$i]=0
    done

    idx=0
    last_log=$(date +%s)

    while true; do

        timestamp=$(date +"%Y-%m-%d %H:%M:%S")

        # CPU RAM
        read -r RAM_USED RAM_FREE <<< "$(free -m | awk '/Mem:/ {print $3, $4}')"

        # GPU metrics
        GPU_QUERY=$(nvidia-smi --id=0 \
            --query-gpu=utilization.gpu,memory.used,memory.free \
            --format=csv,noheader,nounits 2>/dev/null || echo "")

        if [[ -n "$GPU_QUERY" ]]; then
            IFS=',' read -r GPU_UTIL GPU_MEM_USED GPU_MEM_FREE <<< "${GPU_QUERY// /}"
        else
            GPU_UTIL=0
            GPU_MEM_USED=0
            GPU_MEM_FREE=0
        fi

        # Instant GFLOPS estimate
        EST_GFLOPS=$(awk -v peak="$PEAK_FLOPS" -v util="$GPU_UTIL" \
            'BEGIN { printf "%.6f", peak * (util / 100.0) }')

        FLOP_WINDOW[$idx]=$EST_GFLOPS
        idx=$(( (idx + 1) % WINDOW ))

        sum=0
        for val in "${FLOP_WINDOW[@]}"; do
            sum=$(awk -v s="$sum" -v v="$val" 'BEGIN {print s+v}')
        done
        MOVING_AVG=$(awk -v s="$sum" -v w="$WINDOW" 'BEGIN {printf "%.6f", s/w}')

        now=$(date +%s)

        # Integer comparison → no bc needed
        if (( now - last_log >= LOG_INTERVAL )); then
            echo "$timestamp,$RAM_USED,$RAM_FREE,$GPU_MEM_USED,$GPU_MEM_FREE,$GPU_TOTAL,$GPU_UTIL,$EST_GFLOPS,$MOVING_AVG" >> "$LOGFILE"
            last_log=$now
        fi

        sleep "$SAMPLE_INTERVAL"
    done
}

monitor_resources &
MONITOR_PID=$!

# Ensure monitor is killed if job exits unexpectedly
cleanup() {
    kill "$MONITOR_PID" 2>/dev/null || true
}
trap cleanup EXIT

START_TIME=$(date +%s)

julia -t "$SLURM_CPUS_PER_TASK" --project=. run.jl global 1990 1994 --nc

END_TIME=$(date +%s)
RUNTIME=$((END_TIME - START_TIME))

cleanup

TOTAL_ESTIMATE=$(awk -v peak="$PEAK_FLOPS" -v t="$RUNTIME" \
    'BEGIN { if (t>0) printf "%.2f", peak * 0.5 * (t/3600.0); else print 0 }')

{
echo "==============================================="
echo "Total runtime (s): $RUNTIME"
echo "GPU total VRAM (MiB): $GPU_TOTAL"
echo "(rough) Estimated average GFLOPS: ~$TOTAL_ESTIMATE"
echo "See $LOGFILE for detailed time series"
echo "==============================================="
} | tee "$SUMMARYFILE"

echo "Finished at: $(date)"
