#!/bin/bash
#SBATCH --job-name=merge_global
#SBATCH --partition=main
#SBATCH --time=3-00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=512G
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/merge_Global_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/merge_Global_%j.err

# CPU setup
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}

# Load modules
module purge
module load legacy
module load ncview/gcc/64/2.1.7
module load cdo/gcc/64/1.9.3
module load nco

# Define directories
INDIR=/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global/file_by_year
OUTDIR=/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global
TMPDIR=${OUTDIR}/tmp_reordered
mkdir -p "${OUTDIR}"
mkdir -p "${TMPDIR}"

echo "[$(date)] Starting dimension fix and merge..."
echo "CDO version: $(cdo -V)"
echo "NCO version: $(ncks --version)"

# Loop over all files to reorder dimensions where needed
for f in "${INDIR}"/mGV_global_NH_NR_DP_S*.nc; do
    base=$(basename "$f")
    tmp="${TMPDIR}/$base"
    echo "Processing $base..."

    # Reorder variables where time is not first
    ncpdq -O -a time,qlayers,lat,lon \
          -a time,top_layer,lat,lon \
          -a time,layer,lat,lon \
          "$f" "$tmp"

    # Optional: set time axis if missing
    # cdo settaxis,1990-01-01,00:00:00,1day "$tmp" "$tmp"  # uncomment if needed
done

# Merge all fixed files
cdo -V -L -P ${SLURM_CPUS_PER_TASK} mergetime "${TMPDIR}"/mGV_global_NH_NR_DP_S*.nc \
    "${OUTDIR}"/mGV_global_NH_NR_DP_S10.nc

echo "[$(date)] Merge finished."

