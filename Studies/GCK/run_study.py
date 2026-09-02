from pathlib import Path
import glob
import shutil
import argparse

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

    completed_trials = []
    for i, result in enumerate(results):
        if result['task_processtime'] == 0: 
            continue
        if 'ERROR' in result:
            if log:=result.get("task_logfile"):
                mf = mainfiles[i]
                try:
                    display = mf.relative_to(Path.cwd()) if mf.is_absolute() else mf
                except Exception:
                    display = mf
                print(f"Failed: {display} ( [blue]{log}[/blue] )")
            continue
        
        completed_trials.append(mainfiles[i])

    return completed_trials


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

    # Static phase
    if run_static:
        pattern: str = "Studies/GCK/Subjects/*/Trials Static/*/main.any"
        mainfiles = find_files(pattern)
        if mainfiles:
            print("Found the following main.any files for static reference trials:")
            for p in mainfiles:
                print(f" - {p}")
        else:
            print("No static trials found.")

        if mainfiles:
            run_anybody_code(mainfiles, operation="Main.RunParameterIdentification", logfile="logs/staticref.txt")

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

    