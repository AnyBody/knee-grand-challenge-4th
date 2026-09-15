from pathlib import Path
import glob
import shutil
import argparse
import re

from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, OperationRun
from rich import print


def run_anybody_code(mainfiles: list[Path], operation: str, logfile: str, **kwargs) -> list[Path]:

    if not mainfiles: 
        print("No trials found.")
        return []

    macros = []
    for mainfile in mainfiles:
        macros.append(
            [
                Load(mainfile),
                OperationRun(operation),
            ]
        )
    app = AnyPyProcess(**kwargs)

    logfile = Path(logfile).absolute()
    # Ensure logfile directory exists so AnyPyProcess can create per-task logfiles
    logfile.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Running {len(mainfiles)} trial(s) with: '{operation}'...")
    results = app.start_macro(macros, logfile=logfile)

    failed_trials = []
    completed_trials = []
    for i, result in enumerate(results):
        if result['task_processtime'] == 0: 
            continue
        if 'ERROR' in result:
            mf = mainfiles[i]
            try:
                display = mf.relative_to(Path.cwd()) if mf.is_absolute() else mf
            except Exception:
                display = mf

            error_msg = result['ERROR']
            log = result.get("task_logfile")
            if log:
                print(f"Failed: {display} ( [blue]{log}[/blue] )\n  ERROR: {error_msg}")
            else:
                print(f"Failed: {display}\n  ERROR: {error_msg}")
            failed_trials.append((display, error_msg))
            continue
        
        completed_trials.append(mainfiles[i])

    if failed_trials:
        summary = "\n".join(
            f"  - {mf}: {err}" for mf, err in failed_trials
        )
        raise RuntimeError(
            f"{len(failed_trials)} trial(s) failed during '{operation}':\n{summary}"
        )

    return completed_trials


def _parse_load_parameters_from(trial_specific_file: Path) -> str | None:
    """Extract the LoadParametersFrom string from a TrialSpecificData.any file."""
    text = trial_specific_file.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'LoadParametersFrom\s*=\s*\{\s*"([^"]+)"\s*\}\s*;', text)
    return match.group(1) if match else None


def _normalize_mainfile(path: Path) -> Path:
    """Return a canonical path, preferring relative-to-cwd when possible."""
    absolute = path.resolve()
    try:
        return absolute.relative_to(Path.cwd())
    except ValueError:
        return absolute


def _resolve_parameter_id_mainfiles(dynamic_mainfiles: list[Path]) -> list[Path]:
    """
    Decide which mainfiles to run for parameter identification.

    For each dynamic trial, inspect TrialSpecificData.any:
    - If LoadParametersFrom points to a Trials Static file, run that static trial's Main.any.
    - Otherwise, run the dynamic trial itself.

    Returns a deduplicated list of mainfiles.
    """
    seen: set[Path] = set()
    mainfiles: list[Path] = []

    for dyn_main in sorted(dynamic_mainfiles):
        dyn_dir = dyn_main.parent
        trial_specific = dyn_dir / "TrialSpecificData.any"

        if not trial_specific.exists():
            normalized = _normalize_mainfile(dyn_main)
            if normalized not in seen:
                seen.add(normalized)
                mainfiles.append(normalized)
            continue

        load_from = _parse_load_parameters_from(trial_specific)

        if load_from is None:
            normalized = _normalize_mainfile(dyn_main)
            if normalized not in seen:
                seen.add(normalized)
                mainfiles.append(normalized)
            continue

        # A path-like reference (e.g. "../../Trials Static/PS_staticfor1/PS_staticfor1")
        # indicates parameters are loaded from a static reference trial.
        if "Trials Static" in load_from or "/" in load_from or "\\" in load_from:
            ref_path = (dyn_dir / load_from).resolve()
            static_main = ref_path.parent / "Main.any"
            if not static_main.exists():
                # Fallback: try the dynamic trial itself if the static main is missing
                static_main = dyn_main
        else:
            # Local reference: use the dynamic trial's own main file
            static_main = dyn_main

        normalized = _normalize_mainfile(static_main)
        if normalized not in seen:
            seen.add(normalized)
            mainfiles.append(normalized)

    return mainfiles


def find_files(pattern: str, root='.') -> list[Path]:
    """
    Find files matching a shell-style wildcard pattern relative to `root`.

    Example: "Subjects/*/Trials Static/*_ref/main.any"

    Returns a list of pathlib.Path objects.
    """
    root_path = Path(root)
    # Normalize pattern: if it's not absolute, make it relative to root
    patt = pattern
    if not Path(pattern).is_absolute():
        patt = str(root_path / pattern)

    recursive = "**" in pattern
    matches = glob.glob(patt, recursive=recursive)
    return [Path(m) for m in sorted(matches)]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GCK study phases: static, dynamic, postprocess")
    parser.add_argument("--static", action="store_true", help="Run static reference trials (parameter identification)")
    parser.add_argument("--dynamic", action="store_true", help="Run dynamic trials (analysis)")
    parser.add_argument("--postprocess", action="store_true", help="Only run postprocessing (copy results)")
    args = parser.parse_args()

    # If no flags provided, run all phases
    requested = args.static or args.dynamic or args.postprocess
    run_static = args.static or not requested
    run_dynamic = args.dynamic or not requested
    run_post = args.postprocess or not requested

    # Static phase: parameter identification
    # For each dynamic trial, check TrialSpecificData.any. If LoadParametersFrom
    # points to a static reference trial, run that static trial's Main.any;
    # otherwise run the dynamic trial itself.
    if run_static:
        dynamic_pattern: str = "Studies/GCK/Subjects/*/Trials Dynamic/*/main.any"
        dynamic_mainfiles = find_files(dynamic_pattern)

        if dynamic_mainfiles:
            mainfiles = _resolve_parameter_id_mainfiles(dynamic_mainfiles)
            print("Running parameter identification for the following trials:")
            for p in mainfiles:
                print(f" - {p}")
            run_anybody_code(mainfiles, operation="Main.RunParameterIdentification", logfile="logs/staticref.txt")
        else:
            print("No dynamic trials found for parameter identification.")

    # Dynamic phase
    if run_dynamic:
        pattern: str = "Studies/GCK/Subjects/*/Trials Dynamic/*/main.any"
        mainfiles = find_files(pattern)
        if mainfiles:
            print("Found the following main.any files for dynamic trials:")
            for p in mainfiles:
                print(f" - {p}")
        else:
            print("No dynamic trials found.")

        if mainfiles:
            run_anybody_code(mainfiles, operation="Main.RunAnalysis", logfile="logs/dynamic.txt")

    # Postprocessing: collect inverse dynamic study files and copy to Results/
    if run_post:
        pattern: str = "Studies/GCK/Subjects/*/Trials Dynamic/*/*InverseDynamicStudy.anydata.h5"
        datafiles = find_files(pattern)
        if datafiles:
            print("Found the following result files:")
            for p in datafiles:
                print(f" - {p}")

            results_root = Path("Results")
            copied = []
            for p in datafiles:
                try:
                    rel = p.relative_to(Path.cwd()) if p.is_absolute() else p
                except Exception:
                    rel = p
                dest = results_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(p, dest)
                    copied.append(dest)
                except Exception as e:
                    print(f"Failed to copy {p} -> {dest}: {e}")

            if copied:
                print("Copied the following files to Results:")
                for c in copied:
                    print(f" - {c}")
            else:
                print("No files were copied to Results.")
        else:
            print(Path.cwd())
            print("No result files found for postprocessing.")

    