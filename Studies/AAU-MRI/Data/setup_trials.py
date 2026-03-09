import ezc3d
import shutil
from pathlib import Path
import re
import sys
import subprocess
import shlex
import glob
import os

# Local reference/template patient folder (use a local folder named REF_PATIENT)
REF_PATIENT = Path('REF_PATIENT')


def create_reference_c3d(input_path, output_path, start_frame, end_frame):
    """Create a reference C3D containing only frames [start_frame, end_frame] (1-indexed).

    Keeps both point and analog ranges consistent.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    print("=" * 80)
    print(f"Creating reference file: {output_path}")
    print(f"From: {input_path}")
    print(f"Frame range: {start_frame} to {end_frame}")
    print("=" * 80)

    c3d = ezc3d.c3d(str(input_path))

    analog_rate = c3d["parameters"]["ANALOG"]["RATE"]["value"][0]
    point_rate = c3d["parameters"]["POINT"]["RATE"]["value"][0]
    samples_per_frame = int(analog_rate / point_rate)

    start_idx = start_frame - 1
    end_idx = end_frame

    # Keep original frame count for meta_points handling
    orig_frames = c3d["data"]["points"].shape[2]
    point_data = c3d["data"]["points"][:, :, start_idx:end_idx]
    analog_start = start_idx * samples_per_frame
    analog_end = end_idx * samples_per_frame
    analog_data = c3d["data"]["analogs"][:, :, analog_start:analog_end]

    c3d["data"]["points"] = point_data
    c3d["data"]["analogs"] = analog_data
    # Try to adjust meta_points to match the new frame count by slicing any
    # arrays that have a trailing frame dimension. If that fails, remove only
    # the problematic 'residuals' entry so ezc3d can regenerate consistent
    # metadata on write.
    try:
        # Obtain meta_points from c3d data (supports mapping-like or attribute)
        try:
            meta = c3d["data"]["meta_points"]
        except Exception:
            meta = getattr(c3d["data"], "meta_points", None)

        if meta is not None:
            try:
                import numpy as _np
                # If meta is mapping-like, iterate keys and slice arrays where
                # the last dimension corresponds to the original frame count.
                if hasattr(meta, "items"):
                    for key, val in list(meta.items()):
                        if hasattr(val, "ndim") and val.ndim >= 3:
                            if val.shape[-1] == orig_frames:
                                meta[key] = val[..., start_idx:end_idx]
                else:
                    # If meta is not mapping-like, attempt to adjust common fields
                    if hasattr(meta, "residuals"):
                        val = meta.residuals
                        if hasattr(val, "ndim") and val.ndim >= 3 and val.shape[-1] == orig_frames:
                            meta.residuals = val[..., start_idx:end_idx]

                # write back adjusted meta_points
                try:
                    c3d["data"]["meta_points"] = meta
                except Exception:
                    try:
                        setattr(c3d["data"], "meta_points", meta)
                    except Exception:
                        pass
            except Exception:
                # Fallback: remove only residuals entry which commonly causes
                # frame-count mismatch errors so ezc3d can regenerate metadata.
                try:
                    if isinstance(c3d["data"], dict):
                        if "meta_points" in c3d["data"] and "residuals" in c3d["data"]["meta_points"]:
                            del c3d["data"]["meta_points"]["residuals"]
                    else:
                        mp = getattr(c3d["data"], "meta_points", None)
                        if mp and "residuals" in mp:
                            del mp["residuals"]
                except Exception:
                    pass
    except Exception:
        # Be conservative: if anything unexpected happens, do not modify meta.
        pass

    new_frame_count = end_idx - start_idx
    c3d["parameters"]["POINT"]["FRAMES"]["value"] = [new_frame_count]

    print(f"Extracted {new_frame_count} frames")
    print(f"Point data shape: {point_data.shape}")
    print(f"Analog data shape: {analog_data.shape}")

    c3d.write(str(output_path))
    print(f"[OK] Created reference file: {output_path}")
    print("=" * 80)

def setup_subject_folder(patient_id, info):
    """
    Create subject folder structure and copy necessary files.
    
    Parameters:
    -----------
    patient_id : str
        Patient ID (e.g., "PAT0123")
    info : list
        [c3d_file, stl_folder, sim_start, sim_end, ref_start, ref_end, body_height, body_mass]
    """
    print("=" * 80)
    print(f"Setting up folder structure for {patient_id}")
    print("=" * 80)

    c3d_file = str(info[0])
    raw_side = str(info[1]).lower()
    body_height_cm = info[6]
    body_mass_kg = info[7]

    if 'right' in raw_side:
        leg_side = 'right'
    elif 'left' in raw_side:
        leg_side = 'left'
    else:
        leg_side = 'right' if 'right' in c3d_file.lower() else 'left'

    subject_folder = Path('../Subjects') / patient_id
    subject_folder.mkdir(parents=True, exist_ok=True)
    print(f"Created/verified folder: {subject_folder}")

    body_height_m = body_height_cm / 100.0

    ssd_src = Path('REF_PATIENT/SubjectSpecificData.any')
    if ssd_src.exists():
        subject_content = ssd_src.read_text()
        subject_content = re.sub(r'BodyMass = [\d.]+;', f'BodyMass = {body_mass_kg};', subject_content)
        subject_content = re.sub(r'BodyHeight = [\d.]+;', f'BodyHeight = {body_height_m};', subject_content)
        (subject_folder / 'SubjectSpecificData.any').write_text(subject_content)
        print(f"Copied and updated SubjectSpecificData.any to {subject_folder}")
        print(f"  - BodyHeight: {body_height_cm} cm -> {body_height_m} m")
        print(f"  - BodyMass: {body_mass_kg} kg")
    else:
        print('Warning: SubjectSpecificData.any not found; skipping')

    trials_static_folder = subject_folder / 'Trials Static' / f"{patient_id}_ref"
    trials_static_folder.mkdir(parents=True, exist_ok=True)
    print(f"Created/verified folder: {trials_static_folder}")

    if Path('REF_PATIENT/main.any').exists():
        shutil.copy2('main.any', trials_static_folder / 'main.any')
        print(f"Copied main.any to {trials_static_folder}")
    else:
        print('Warning: main.any not found; skipping')

    ref_source = c3d_file.replace('postop_stepup.c3d', 'ref.c3d').replace('preop_stepup.c3d', 'ref.c3d')
    ref_dest = trials_static_folder / f"{patient_id}_ref.c3d"
    try:
        shutil.copy2(ref_source, ref_dest)
        print(f"Copied {ref_source} to {ref_dest}")
    except Exception:
        print(f"Warning: could not copy reference C3D from {ref_source}")

    ts_src = Path('REF_PATIENT/TrialSpecificData.any')
    if ts_src.exists():
        content = ts_src.read_text()
        content = content.replace('LoadParametersFrom = {"..\\..\\Trials Static\\REF_PATIENT_ref"};',
                                  '//LoadParametersFrom = {"..\\..\\Trials Static\\REF_PATIENT_ref"};')
        right_on = 'ON' if leg_side == 'right' else 'OFF'
        left_on = 'ON' if leg_side == 'left' else 'OFF'
        content = re.sub(r'#define\s+BM_LEG_RIGHT\s+(ON|OFF)', f'#define BM_LEG_RIGHT {right_on}', content)
        content = re.sub(r'#define\s+BM_LEG_LEFT\s+(ON|OFF)', f'#define BM_LEG_LEFT {left_on}', content)
        content = content.replace('//nStep = ;', 'nStep = 5;')
        content = re.sub(r'FirstFrame = \d+;', 'FirstFrame = .C3DFileData.Header.FirstFrameNo+5;', content)
        content = re.sub(r'LastFrame = \d+;', 'LastFrame = .C3DFileData.Header.LastFrameNo-5;', content)
        (trials_static_folder / 'TrialSpecificData.any').write_text(content)
        print(f"Created {trials_static_folder / 'TrialSpecificData.any'} with:")
        print(f"  - Leg: {leg_side.upper()}")
        print(f"  - FirstFrame: .C3DFileData.Header.FirstFrameNo+5")
        print(f"  - LastFrame: .C3DFileData.Header.LastFrameNo-5")
    else:
        print('Warning: TrialSpecificData.any not found; skipping')

    print(f"[OK] Setup complete for {patient_id}")
    print("=" * 80)

def setup_dynamic_trial_folder(patient_id, info):
    """
    Create dynamic trial folder structure and copy necessary files.
    
    Parameters:
    -----------
    patient_id : str
        Patient ID (e.g., "PAT3032")
    info : list
        [c3d_file, sim_start, sim_end, ref_start, ref_end, body_height, body_mass]
    """
    print("=" * 80)
    print(f"Setting up dynamic trial folder for {patient_id}")
    print("=" * 80)
    # Determine leg side and simulation indices, supporting old/new name_dict formats
    c3d_file = info[0]
    raw_side = str(info[1]).lower()
    sim_start = info[2]
    sim_end = info[3]


    # raw_side may be a patient subfolder path; search for 'right'/'left' anywhere
    if 'right' in raw_side:
        leg_side = 'right'
    elif 'left' in raw_side:
        leg_side = 'left'
    else:
        leg_side = "right" if "right" in c3d_file.lower() else "left"
    
    # Extract trial type from c3d filename (preop_stepup or postop_stepup)
    if "preop_stepup" in c3d_file.lower():
        trial_type = "preop_stepup"
    elif "postop_stepup" in c3d_file.lower():
        trial_type = "postop_stepup"
    else:
        trial_type = "stepup"  # fallback
    
    subject_folder = Path('../Subjects') / patient_id
    trials_dynamic_folder = subject_folder / 'Trials Dynamic' / f"{patient_id}_{trial_type}"
    trials_dynamic_folder.mkdir(parents=True, exist_ok=True)
    print(f"Created/verified folder: {trials_dynamic_folder}")

    if Path('REF_PATIENT/main.any').exists():
        shutil.copy2('main.any', trials_dynamic_folder / 'main.any')
        print(f"Copied main.any to {trials_dynamic_folder}")
    else:
        print('Warning: main.any not found; skipping')

    c3d_dest = trials_dynamic_folder / f"{patient_id}_{trial_type}.c3d"
    try:
        shutil.copy2(c3d_file, c3d_dest)
        print(f"Copied {c3d_file} to {c3d_dest}")
    except Exception:
        print(f"Warning: could not copy dynamic C3D {c3d_file} to {c3d_dest}")
    
    # Create modified TrialSpecific.any
    # sim_start and sim_end were set above depending on name_dict format
    
    ts_src = Path('REF_PATIENT/TrialSpecificData.any')
    if ts_src.exists():
        content = ts_src.read_text()
        content = content.replace(
            'LoadParametersFrom = {"..\\..\\Trials Static\\REF_PATIENT_ref"};',
            f'LoadParametersFrom = {{"..\\..\\Trials Static\\{patient_id}_ref\\{patient_id}_ref"}};'
        )
        right_on = 'ON' if leg_side == 'right' else 'OFF'
        left_on = 'ON' if leg_side == 'left' else 'OFF'
        content = re.sub(r'#define\s+BM_LEG_RIGHT\s+(ON|OFF)', f'#define BM_LEG_RIGHT {right_on}', content)
        content = re.sub(r'#define\s+BM_LEG_LEFT\s+(ON|OFF)', f'#define BM_LEG_LEFT {left_on}', content)
        content = re.sub(r'FirstFrame = \d+;', f'FirstFrame = {sim_start};', content)
        content = re.sub(r'LastFrame = \d+;', f'LastFrame = {sim_end};', content)
        (trials_dynamic_folder / 'TrialSpecificData.any').write_text(content)
        print(f"Created {trials_dynamic_folder / 'TrialSpecificData.any'} with:")
        print(f"  - Leg: {leg_side.upper()}")
        print(f"  - FirstFrame: {sim_start}")
        print(f"  - LastFrame: {sim_end}")
        print(f"  - LoadParametersFrom: Trials Static/{patient_id}_ref")
    else:
        print('Warning: TrialSpecificData.any not found; skipping')
    
    print(f"[OK] Dynamic trial setup complete for {patient_id}")
    print("="*80)

def run_icp_for_subject(patient_id, info, data_root='.'):
    """Run icp_register.py for a subject using femur/tibia articulation CSVs found in the
    subject folder given by the second entry in `info`.

    This function will look for `femur_articulation.csv`, `tibia_articulation.csv` and
    matching `*femur*.stl`/`*tibia*.stl` files inside the provided folder and invoke
    `icp_register.py` with `--close-after-save` so the process doesn't block.
    """
    # Determine candidate folder from info[1]
    candidate = str(info[1]) if len(info) >= 2 else ''
    cand_path = Path(candidate)
    if not cand_path.exists():
        cand_path = Path(data_root) / candidate
    if not cand_path.exists():
        found = None
        for p in Path(data_root).iterdir():
            if p.is_dir() and patient_id.lower() in p.name.lower():
                found = p
                break
        if found is not None:
            cand_path = found
            print(f'Found subject folder for {patient_id} by search: {cand_path}')
        else:
            print(f'No subject folder found for {patient_id} at "{candidate}" — skipping ICP')
            return

    fem_csv = cand_path / 'femur_articulation.csv'
    tib_csv = cand_path / 'tibia_articulation.csv'
    if not fem_csv.exists() or not tib_csv.exists():
        print(f'Missing femur/tibia CSV for {patient_id} in {cand_path} — skipping ICP')
        return

    fem_stl = None
    tib_stl = None
    for p in cand_path.glob('*.stl'):
        name = p.name.lower()
        if 'femur' in name and fem_stl is None:
            fem_stl = p
        if 'tibia' in name and tib_stl is None:
            tib_stl = p

    if fem_stl is None or tib_stl is None:
        print(f'Missing femur/tibia STL in {cand_path} — skipping ICP for {patient_id}')
        return

    runner = Path(__file__).resolve().parent / 'icp_register.py'
    if not runner.exists():
        alt = Path(__file__).resolve().parent / 'ICP' / 'icp_register.py'
        if alt.exists():
            runner = alt
            print(f'Found icp_register.py in ICP subfolder: {runner}')
        else:
            print('Could not find icp_register.py alongside setup_trials.py or in ICP/; skipping ICP')
            return

    try:
        import importlib.util as _il
        has_vtk = _il.find_spec('vtk') is not None
    except Exception:
        has_vtk = False
    runner_exec = sys.executable if has_vtk else 'python'
    if not has_vtk:
        print('Current environment lacks vtk; invoking icp_register.py with system python')

    cmd = [runner_exec, str(runner),
           '--femur-csv', str(fem_csv), '--tibia-csv', str(tib_csv),
           '--femur-stl', str(fem_stl), '--tibia-stl', str(tib_stl),
           '--out-dir', str(cand_path), '--results-name', f'{patient_id}_tf_reg.any',
           '--close-after-save']

    print('Running ICP for', patient_id, ':', ' '.join(shlex.quote(c) for c in cmd))
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
        print('ICP return code for', patient_id, ':', completed.returncode)
        if completed.stdout:
            print('stdout:\n', completed.stdout)
        if completed.stderr:
            print('stderr:\n', completed.stderr)
    except Exception as e:
        print('ICP failed for', patient_id, ':', e)

def copy_template_files(patient_id, info):
    """
    Copy template files and folders from reference patient 2668.
    
    Parameters:
    -----------
    patient_id : str
        Patient ID (e.g., "PAT0123")
    info : list
        [c3d_file, stl_folder, sim_start, sim_end, ref_start, ref_end, body_height, body_mass]
    """
    print("=" * 80)
    print(f"Copying template files for {patient_id}")
    print("=" * 80)

    template_folder = REF_PATIENT
    ref_name = template_folder.name
    subject_folder = Path("../Subjects") / patient_id

    folders_to_copy = ["JointContact", "JointFit", "Ligament"]
    for folder in folders_to_copy:
        src = template_folder / folder
        dst = subject_folder / folder
        if patient_id != ref_name and src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied {folder} folder")
        else:
            dst.mkdir(parents=True, exist_ok=True)
            print(f"Created empty {folder} folder")

    morphing_source_src = template_folder / 'Morphing' / 'Source'
    morphing_source_dst = subject_folder / 'Morphing' / 'Source'
    if patient_id != ref_name and morphing_source_src.exists():
        (subject_folder / 'Morphing').mkdir(parents=True, exist_ok=True)
        if morphing_source_dst.exists():
            shutil.rmtree(morphing_source_dst)
        shutil.copytree(morphing_source_src, morphing_source_dst)
        print(f"Copied Morphing/Source folder")
    else:
        morphing_source_dst.mkdir(parents=True, exist_ok=True)
        print(f"Created empty Morphing/Source folder")

    morphing_target_dst = subject_folder / 'Morphing' / 'Target'
    morphing_target_dst.mkdir(parents=True, exist_ok=True)
    print(f"Created Morphing/Target folder")

    dataconfig_src = template_folder / 'Morphing' / 'DataConfig.any'
    dataconfig_dst = subject_folder / 'Morphing' / 'DataConfig.any'
    if patient_id != ref_name and dataconfig_src.exists():
        shutil.copy2(dataconfig_src, dataconfig_dst)
        print(f"Copied Morphing/DataConfig.any")
    else:
        dataconfig_dst.write_text("// Morphing configuration file\n#include \"<LAB_CONFIG_PATH>/Morphing/DataConfig.any\"\n")
        print(f"Created dummy Morphing/DataConfig.any")

    jointfit_dataconfig_src = template_folder / 'JointFit' / 'DataConfig.any'
    jointfit_dataconfig_dst = subject_folder / 'JointFit' / 'DataConfig.any'
    if patient_id != ref_name and jointfit_dataconfig_src.exists():
        shutil.copy2(jointfit_dataconfig_src, jointfit_dataconfig_dst)
        print(f"Copied JointFit/DataConfig.any")
    else:
        jointfit_dataconfig_dst.write_text("// JointFit configuration file\n#include \"<LAB_CONFIG_PATH>/JointFit/DataConfig.any\"\n")
        print(f"Created JointFit/DataConfig.any")

    c3d_file = str(info[0])
    c3d_folder = Path(c3d_file).parent
    stl_folder = None
    if len(info) > 1:
        candidate = str(info[1])
        if Path(candidate).is_dir():
            stl_folder = Path(candidate)
    if stl_folder is None:
        stl_folder = c3d_folder
    stl_files = list(stl_folder.glob('*.stl'))
    if stl_folder != c3d_folder:
        print(f"Using STL folder from info[1]: {stl_folder}")

    if stl_files:
        for stl_file in stl_files:
            dst_stl = morphing_target_dst / stl_file.name
            shutil.copy2(stl_file, dst_stl)
        print(f"Copied {len(stl_files)} STL files to Morphing/Target")
    else:
        print(f"Warning: No STL files found in {stl_folder}")

    print(f"[OK] Template files copied for {patient_id}")
    print("=" * 80)

if __name__ == "__main__":

    C3Ds = "C3D_New"  # Base folder for C3D files
    name_dict = {
        "PAT2668": [C3Ds+"/PAT2668_postop_stepup.c3d", "1_18_PAT2668_right", 1100, 1778, 1370-205, 1420+205, 154, 66],
        "PAT3041": [C3Ds+"/PAT3041_preop_stepup.c3d", "3_39_PAT3041_left", 1499, 2192, 1805-205, 1855+205, 184, 90],
        "PAT3112": [C3Ds+"/PAT3112_preop_stepup.c3d", "4_41_PAT3112_left", 1289, 2187, 1690-205, 1740+205, 169, 71],
        "PAT3405": [C3Ds+"/PAT3405_preop_stepup.c3d", "6_46_PAT3405_left", 1257, 1936, 1526-205, 1576+205, 177, 80],
        "PAT3477": [C3Ds+"/PAT3477_preop_stepup.c3d", "8_48_PAT3477_left", 1249, 2028, 1348-205, 1798+205, 170, 85],
    }

    # Run ICP on each subject prior to other processing (uses subject folder from info[1])
    print('\nRunning ICP pre-processing on subjects (this runs icp_register.py)...')
    for k, v in name_dict.items():
        try:
            run_icp_for_subject(k, v, data_root='./ICP/')

            # After ICP run, try to locate the produced tf_reg file and copy it
            # into ../Subjects/<PAT>/Morphing/Target/tf_reg.any so Subjects contains it.
            tf_found = None
            # look for patient-specific named file first
            for p in Path('.').glob(f'**/{k}_tf_reg.any'):
                tf_found = p
                break

            if tf_found is not None:
                dest_dir = Path('../Subjects') / k / 'Morphing' / 'Target'
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / 'tf_reg.any'
                try:
                    shutil.copy2(tf_found, dest_path)
                    print(f'Copied ICP result {tf_found} -> {dest_path}')
                except Exception as e:
                    print(f'Failed to copy {tf_found} to {dest_path}:', e)
            else:
                print(f'No tf_reg file found for {k} after ICP — expected e.g. {k}_tf_reg.any')

            print()
        except Exception as e:
            print(f'ERROR running ICP for {k}: {e}')
            import traceback
            traceback.print_exc()
            print()

    # Create reference files only (no fixing needed)
    for k, v in name_dict.items():
        input_file = v[0]
        output_ref_file = input_file.replace("postop_stepup.c3d", "ref.c3d").replace("preop_stepup.c3d", "ref.c3d") #replace whether this is preop or postop
        
        try:
            # Create reference trial from original C3D file
            # support old and new name_dict formats
            if len(v) >= 8:
                ref_start = v[4]
                ref_end = v[5]
            else:
                ref_start = v[3]  # Static ref start frame
                ref_end = v[4]    # Static ref end frame
            create_reference_c3d(input_file, output_ref_file, ref_start, ref_end)

            print()
        except Exception as e:
            print(f"ERROR processing {input_file}: {e}")
            print()

    print("="*80)
    print("All reference files created!")
    print("="*80)
    
    # Setup subject folder structures
    for patient_id, info in name_dict.items():
        try:
            setup_subject_folder(patient_id, info)
            print()
        except Exception as e:
            print(f"ERROR setting up folder for {patient_id}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("="*80)
    print("All subject folders created!")
    print("="*80)
    
    # Setup dynamic trial folder structures
    for patient_id, info in name_dict.items():
        try:
            setup_dynamic_trial_folder(patient_id, info)
            print()
        except Exception as e:
            print(f"ERROR setting up dynamic trial for {patient_id}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("="*80)
    print("All dynamic trial folders created!")
    print("="*80)
    
    # Copy template files from patient 2668
    for patient_id, info in name_dict.items():
        try:
            copy_template_files(patient_id, info)
            print()
        except Exception as e:
            print(f"ERROR copying template files for {patient_id}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("="*80)
    print("All template files copied!")
    print("="*80)



