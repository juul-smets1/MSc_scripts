#!/bin/bash
#SBATCH --job-name=remap_tair
#SBATCH --partition=main
#SBATCH --time=1-00:00
#SBATCH --cpus-per-task=12
#SBATCH --mem=32G
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mekong_remap/logs/tair_remap_%j.txt
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/mekong_remap/logs/tair_remap_%j.err

set -euo pipefail

# --- Input / Output paths ---
forcing_indir="/lustre/backup/WUR/ESG/data/MODEL_DATA/VIC/FORCING/VICWUR/WFDE5/daily/tas_daily_WFDE5_CRU"
static_indir="/lustre/nobackup/WUR/ESG/marin052/isimip3b/input"
clone="$static_indir/clone_5m_global.nc"
mask="$static_indir/mask_5m_global.nc"

OUTDIR="/lustre/nobackup/WUR/ESG/smets008/mGV/input_data/mekong/forcing/tair"
VALIDDIR="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/mekong/02forcing/tair"
mkdir -p "$OUTDIR" "$VALIDDIR"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

LONMIN=104
LONMAX=107
LATMIN=8.5
LATMAX=11.5

module purge
module load cdo/gcc/64/1.9.3
module load nco

# Check clone + mask
if [ ! -f "$clone" ]; then
  echo "ERROR: Clone grid not found: $clone"
  exit 1
fi

if [ ! -f "$mask" ]; then
  echo "ERROR: Mask file not found: $mask"
  exit 1
fi

echo "Using clone grid: $clone"
cdo sinfo "$clone"

for YEAR in $(seq 1990 2019); do
  infile="${forcing_indir}/tas_daily_WFDE5_CRU_${YEAR}.nc"
  tmp="${OUTDIR}/tair_WFDE5_5arcmin_${YEAR}.nc"
  tmp_masked="${OUTDIR}/tair_WFDE5_masked_${YEAR}.nc"
  out="${OUTDIR}/tair_WFDE5_Mekong_${YEAR}.nc"

  if [ ! -f "$infile" ]; then
    echo "Missing input: $infile"
    continue
  fi

  echo ">>> Processing TAIR ${YEAR}..."

  # Combined step 1,2,3,4:
  cdo -O -P $SLURM_CPUS_PER_TASK setmissval,-9999 -sellonlatbox,$LONMIN,$LONMAX,$LATMIN,$LATMAX -ifthen $mask -remapbil,$clone -setmisstonn "$infile" "$out"

  # Step 5: Metadata
  ncatted -h -O -a title,global,o,c,"WFDE5 daily average near surface air temperature remapped to HydroSHEDS 5-arcmin grid with land mask applied" "$out"
  ncatted -h -O -a contact,global,o,c,"smets008" "$out"

  # Move + clean
  cp -f "$out" "$VALIDDIR"/

  echo "Finished ${YEAR}"
done

