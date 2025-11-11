#!/bin/bash
# ================================================================
# Script: process_WFDE5_to_5arcmin.sh
# Description: Crop, interpolate, and output WFDE5 forcing data
#              exactly to the Mekong study area at 5 arcmin resolution
# Memory-efficient version: splits cropping and remapping into two steps
# Author: smets008
# ================================================================

# Define your study area crop box
LATMIN=8.54167
LATMAX=11.4583
LONMIN=104.042
LONMAX=106.958

# Define directories
INDIR=/lustre/backup/WUR/ESG/data/MODEL_DATA/VIC/FORCING/VICWUR/WFDE5/daily
OUTDIR1=/lustre/nobackup/WUR/ESG/smets008/mGV/input_data/mekong/forcing
OUTDIR2=/lustre/nobackup/WUR/ESG/smets008/mGV/validations/mekong/02forcing
TMPDIR=/lustre/nobackup/WUR/ESG/smets008/temporary

# Create a 5-arcmin study area grid file (one-time)
GRIDFILE=$TMPDIR/grid_from_model.txt
if [ ! -f $GRIDFILE ]; then
    echo "Creating study-area-specific 5-arcmin grid for the Mekong..."
    cat > $GRIDFILE << EOF
gridtype = lonlat
xsize = 36   # number of 5-arcmin cells in longitude (~3 degrees)
ysize = 36   # number of 5-arcmin cells in latitude (~3 degrees)
xfirst = 104.042
xinc = 0.083333
yfirst = 8.54167
yinc = 0.083333
EOF
fi

# Loop through all variables
for VAR in lwdown_daily_WFDE5_CRU pr_daily_WFDE5_CRU psurf_daily_WFDE5_CRU swdown_daily_WFDE5_CRU vp_daily_WFDE5_CRU tas_daily_WFDE5_CRU wind_daily_WFDE5_CRU; do

    # Map input variable to target folder name
    case $VAR in
        pr_daily_WFDE5_CRU) TARGETDIR=prec ;;
        tas_daily_WFDE5_CRU) TARGETDIR=tair ;;
        vp_daily_WFDE5_CRU) TARGETDIR=vp ;;
        *) TARGETDIR=${VAR%%_*} ;;
    esac

    echo "Processing variable: $VAR -> $TARGETDIR"

    # Create output directories if not exist
    mkdir -p $OUTDIR1/$TARGETDIR $OUTDIR2/$TARGETDIR

    # Loop through years 1990–2019
    for YEAR in $(seq 1990 2019); do
        INFILE=${INDIR}/${VAR}/${VAR}_${YEAR}.nc
        TEMPCROP=${TMPDIR}/temp_crop_${TARGETDIR}_${YEAR}.nc
        TEMP_REMAP=${TMPDIR}/temp_remap_${TARGETDIR}_${YEAR}.nc
        OUTFILE=${OUTDIR1}/${TARGETDIR}/${TARGETDIR}_Mekong_WFDE5_5_arcmin_${YEAR}.nc

        if [ -f "$INFILE" ]; then
            echo "  Cropping $INFILE to study area..."
            cdo -s sellonlatbox,$LONMIN,$LONMAX,$LATMIN,$LATMAX $INFILE $TEMPCROP

            echo "  Remapping $TEMPCROP to 5-arcmin grid over Mekong..."
            if [[ "$VAR" == "pr_daily_WFDE5_CRU" ]] || [[ "$VAR" == "vp_daily_WFDE5_CRU" ]]; then
                cdo -s remapcon,$GRIDFILE $TEMPCROP $TEMP_REMAP
            else
                cdo -s remapbil,$GRIDFILE $TEMPCROP $TEMP_REMAP
            fi

            # Move remapped file to final output
            mv $TEMP_REMAP $OUTFILE

            # Copy to validation folder
            mkdir -p $OUTDIR2/$TARGETDIR
            cp $OUTFILE $OUTDIR2/$TARGETDIR/

            # Clean temporary files
            rm -f $TEMPCROP

        else
            echo "  File not found: $INFILE"
        fi
    done
done

