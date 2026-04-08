# ============================================================
# Script: inspect_viirs_lst_files.py
# Purpose:
# - Inspect the root cause of file reading errors for VIIRS LST files
# - Check directory existence and list .h5 files
# - Verify specific problematic file paths
# - Find similar files based on date and tile
# - Attempt to open an example file and print its HDF5 structure
# - Helps diagnose if files are missing, paths are incorrect, or structure mismatches
# ============================================================
import os
import h5py

# ============================================================
# 1. Define directories (update if needed)
# ============================================================
lst_dir = r"D:\WUR\NASA_ESDS\Yucatán\VIIRS_NPP_Yucatán_LSurfT_Data"
et_dir = r"D:\WUR\NASA_ESDS\Yucatán\VIIRS_NPP_YucatánETData"  # For comparison, since ET works


# ============================================================
# 2. Check if directories exist
# ============================================================
def check_directory(dir_path):
    exists = os.path.exists(dir_path)
    print(f"Directory '{dir_path}' exists: {exists}")
    if exists:
        print(f"Absolute path: {os.path.abspath(dir_path)}")
    return exists


# ============================================================
# 3. List .h5 files in directory
# ============================================================
def list_h5_files(dir_path):
    if not os.path.exists(dir_path):
        return []
    files = [f for f in os.listdir(dir_path) if f.lower().endswith('.h5')]
    print(f"Found {len(files)} .h5 files in '{dir_path}':")
    for f in sorted(files):
        print(f" - {f}")
    return files


# ============================================================
# 4. Check specific problematic file
# ============================================================
def check_specific_file(dir_path, filename):
    file_path = os.path.join(dir_path, filename)
    exists = os.path.exists(file_path)
    print(f"\nChecking file '{filename}' at '{file_path}': exists = {exists}")
    if not exists:
        print(
            "  Possible reasons: file missing, filename mismatch (e.g., different collection/processing suffix), path encoding issue (accents in 'Yucatán'), or permissions.")
    return exists, file_path


# ============================================================
# 5. Find similar files (by date and tile pattern)
# ============================================================
def find_similar_files(files, pattern):
    similar = [f for f in files if pattern in f]
    print(f"\nSimilar files matching pattern '{pattern}': {len(similar)}")
    for f in similar:
        print(f" - {f}")
    return similar


# ============================================================
# 6. Inspect HDF5 file structure
# ============================================================
def inspect_hdf_structure(file_path):
    print(f"\nInspecting structure of '{os.path.basename(file_path)}':")
    try:
        with h5py.File(file_path, 'r') as hdf:
            print("  Root keys:", list(hdf.keys()))
            print("  Full structure:")

            def print_name(name, obj):
                if isinstance(obj, h5py.Dataset):
                    print(f"    Dataset: {name} (shape: {obj.shape}, dtype: {obj.dtype})")
                elif isinstance(obj, h5py.Group):
                    print(f"    Group: {name}")

            hdf.visititems(print_name)
    except Exception as e:
        print(f"  Error opening file: {e}")
        print("  Possible reasons: Not a valid HDF5 file, corrupted, or access denied.")


# ============================================================
# 7. Main inspection
# ============================================================
def main():
    # Check LST directory
    print("=== Inspecting LST Directory ===")
    lst_exists = check_directory(lst_dir)
    if lst_exists:
        lst_files = list_h5_files(lst_dir)

        # Example problematic file from error message
        problem_filename = "VNP21A2.A2012073.h09v06.002.2024104004303.h5"
        exists, problem_path = check_specific_file(lst_dir, problem_filename)

        # Find similar files (ignoring collection/processing suffix)
        pattern = "A2012073.h09v06"
        similar_lst = find_similar_files(lst_files, pattern)

        # If similar files found, inspect the first one
        if similar_lst:
            example_path = os.path.join(lst_dir, similar_lst[0])
            inspect_hdf_structure(example_path)
        elif lst_files:
            # Otherwise, inspect the first available file
            example_path = os.path.join(lst_dir, lst_files[0])
            print("\nNo similar files found; inspecting first available file instead.")
            inspect_hdf_structure(example_path)

    # Check ET directory for comparison (since it works)
    print("\n=== Inspecting ET Directory (for comparison) ===")
    et_exists = check_directory(et_dir)
    if et_exists:
        et_files = list_h5_files(et_dir)

        # Check a similar ET file pattern
        et_pattern = "A2012073.h09v06"
        similar_et = find_similar_files(et_files, et_pattern)

        if similar_et:
            example_et_path = os.path.join(et_dir, similar_et[0])
            inspect_hdf_structure(example_et_path)


# ============================================================
# 8. Run
# ============================================================
if __name__ == "__main__":
    main()