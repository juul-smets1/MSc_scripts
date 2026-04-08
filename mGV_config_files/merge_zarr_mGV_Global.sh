#!/bin/bash
#SBATCH --job-name=merge_global
#SBATCH --partition=main
#SBATCH --time=3-00:00
#SBATCH --cpus-per-task=128
#SBATCH --mem=1000G
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/merge_Global_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mGV_config_files/logs/merge_Global_%j.err

set -euo pipefail

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}

module purge
module load legacy
module load ncview/gcc/64/2.1.7
module load cdo/gcc/64/1.9.3
module load nco

INDIR=/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global/file_by_year
OUTDIR=/lustre/nobackup/WUR/ESG/smets008/zarr_mGV/output_data/global
TMPDIR=${OUTDIR}/tmp_timefixed

mkdir -p "${OUTDIR}"
mkdir -p "${TMPDIR}"

echo "=============================================="
echo "[$(date)] Starting dimension fix and merge"
echo "CDO version : $(cdo -V | head -n 1)"
echo "NCO version : $(ncks --version | head -n 1)"
echo "=============================================="

for f in "${INDIR}"/mGV_global_NH_NR_DP_S*.nc; do
    base=$(basename "$f")
    tmp="${TMPDIR}/${base}"

    echo "[$(date)] Processing file: ${base}"

    # Make 'time' a record (unlimited) dimension
    ncks -O --mk_rec_dmn time "$f" "${tmp}.rec"

    # Reorder dimensions for variables with non-time-first ordering
    # Try to reorder; if variable not present, just warn and continue
    for var in Q12_output soil_evaporation_output soil_temperature_output soil_moisture_output; do
        case "$var" in
            Q12_output) dims="time,qlayers,lat,lon" ;;
            soil_evaporation_output) dims="time,top_layer,lat,lon" ;;
            soil_temperature_output|soil_moisture_output) dims="time,layer,lat,lon" ;;
        esac

        if ! ncpdq -O -v "$var" -a $dims "${tmp}.rec" "${tmp}.rec" 2>/dev/null; then
            echo "[$(date)] Warning: $var not found in $base, skipping reorder"
        fi
    done

    # Move final corrected file
    mv "${tmp}.rec" "$tmp"

    # Validate immediately
    cdo sinfo "$tmp" > /dev/null
done

echo "=============================================="
echo "[$(date)] Dimension fixing completed"
echo "=============================================="

echo "[$(date)] Starting mergetime"
# Low parallelism to avoid HDF5/NetCDF issues
cdo -L -P 4 mergetime "${TMPDIR}"/mGV_global_NH_NR_DP_S*.nc "${OUTDIR}/mGV_global_NH_NR_DP_S10.nc"

echo "=============================================="
echo "[$(date)] Merge finished successfully"
echo "=============================================="

echo "[$(date)] Final file summary:"
cdo sinfo "${OUTDIR}/mGV_global_NH_NR_DP_S10.nc"

