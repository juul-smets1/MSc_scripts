#!/bin/bash
#SBATCH --job-name=n2_VIC_Strong_Scaling_Experiment
#SBATCH --output=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/logs/VIC_Global_ss_MPI256_OpenMP1_%j.out
#SBATCH --error=/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/logs/VIC_Global_ss_MPI256_OpenMP1_%j.err

#SBATCH --partition=main
#SBATCH --nodelist=node[201-272]
#SBATCH --nodes=2
#SBATCH --ntasks=256
#SBATCH --cpus-per-task=1
#SBATCH --time=1-00:00:00
#SBATCH --mem=1000G
#SBATCH --exclusive

echo "Starting VIC Global run: Strong Scale Experiment"
echo "Host: $(hostname)"
echo "Time: $(date)"
echo "------------------------------------------------"

# Load modules
ml 2024
ml OpenMPI/5.0.3-GCC-13.3.0
ml netCDF/4.9.2-gompi-2024a
ml GCC/13.3.0

# OpenMP
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close
echo "Using $OMP_NUM_THREADS OpenMP thread per MPI rank"

# MPI stability: force OB1 + TCP + SM, avoid OFI/OPX
export OMPI_MCA_pml=ob1
export OMPI_MCA_mtl=^ofi
export OMPI_MCA_btl=self,sm,tcp
export OMPI_MCA_mpi_abort_print_stack=1

# Logs
LOGDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/logs"
mkdir -p "$LOGDIR"

# Temporary local directory to reduce Lustre I/O
TMPDIR=/tmp/$USER/$SLURM_JOB_ID
mkdir -p "$TMPDIR"
export VIC_TMP_DIR="$TMPDIR"
cd "$TMPDIR" || { echo "Failed to cd to $TMPDIR"; exit 1; }

# Paths
WORKDIR="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests"
VIC_EXE="/lustre/nobackup/WUR/ESG/smets008/mGV/validations/global/vic_image.exe"
CONFIG="/lustre/nobackup/WUR/ESG/smets008/temporary/MSc_scripts/VIC-WUR_config_files/Strong_scaling_job_requests/vic_global_ss_config.txt"

if [[ ! -x "$VIC_EXE" ]]; then
  echo "ERROR: VIC executable not found or not executable: $VIC_EXE"
  exit 2
fi

# MPI rank distribution
echo "MPI rank distribution:"
srun --mpi=pmix -n $SLURM_NTASKS hostname | sort | uniq -c
echo "------------------------------------------------"

# Run VIC
srun --mpi=pmix --cpu-bind=cores --distribution=block:block -n $SLURM_NTASKS \
     "$VIC_EXE" -g "$CONFIG"

ret=$?

echo "--------------------------------------------------------------------"
echo "VIC Global Strong Scale Experiment finished with exit code: $ret"
echo "Time: $(date)"
exit $ret

