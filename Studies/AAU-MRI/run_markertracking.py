from pathlib import Path

from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, OperationRun, Dump
import typer
import numpy as np
from rich import print


def run_markertracking(mainfiles: list[Path], **kwargs) -> list[Path]:

    if not mainfiles: 
        print("No trials found.")
        return []

    # Ignore any errors from reading in static reference files which
    # contain marker positions which are not in the dynamic trials.
    ignore_errors = ["static_ref.anyset"]
    timevar = "Main.Studies.MarkerTracking.Output.Abscissa.t"
    interpvar = "Main.Studies.MarkerTracking.Output.GaitCycle.Abscissa"
    trialid = "Main.ModelSetup.TrialSpecificData.TrialID"
    subjectid = "Main.ModelSetup.SubjectSpecificData.SubjectID"
    trialtype = "Main.ModelSetup.TrialSpecificData.TrialType"

    marker_error_folder = "Main.Studies.MarkerTracking.Output.MarkerErrors"

    macros = []
    for mainfile in mainfiles:
        macros.append(
            [
                Load(mainfile),
                OperationRun("Main.RunAnalysis.LoadParameters"),
                OperationRun("Main.Studies.MarkerTracking.Kinematics"),
                Dump(timevar),
                Dump(interpvar),
                Dump(trialid),
                Dump(subjectid),
                Dump(trialtype),
                Dump(marker_error_folder),
            ]
        )

    app = AnyPyProcess(ignore_errors=ignore_errors, **kwargs)
    
    print(f"Running {len(mainfiles)} trial(s)...")
    results = app.start_macro(macros, logfile="logs/markertracking.txt")

    completed_trials = []

    for i, result in enumerate(results):
        if result['task_processtime'] == 0:
            continue
        if 'ERROR' in result or timevar not in result:
            if log:=result.get("task_logfile"):
                print(f"Failed: {mainfiles[i].relative_to(Path.cwd())} ( [blue]{log}[/blue] )")
            continue
        
        completed_trials.append(mainfiles[i])

        df = result.to_dataframe(
            index_var=timevar,
            # interp_var=interpvar,
            # interp_val=np.linspace(0, 100, 101),
        )

        # Drop columns containing "..." (from dumping folders from AnyBody)
        # and shorten column names
        df = df.loc[:, df.iloc[0] != "..."]
        df = df.loc[:, ~df.columns.str.startswith("task_")]
        df.columns = df.columns.str.replace("Main.Studies.MarkerTracking.Output.MarkerErrors", "MarkerError")
        df.columns = df.columns.str.replace("Main.ModelSetup.SubjectSpecificData.", "")
        df.columns = df.columns.str.replace("Main.ModelSetup.TrialSpecificData.", "")
        df.columns = df.columns.str.replace("Main.Studies.MarkerTracking.Output.Abscissa.t", "t")
        df.columns = df.columns.str.replace("Main.Studies.MarkerTracking.Output.GaitCycle.Abscissa", "gait_cycle")

        # Trim all data outside events (gait_cycle outside range [0, 100])
        df = df[(df["gait_cycle"] >= 0) & (df["gait_cycle"] <= 100)]
        subject_id = df["SubjectID"].iloc[0]
        trial_id = df["TrialID"].iloc[0]

        outputfolder = Path("Results/markertracking")
        outputfolder.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(outputfolder / f"{subject_id}_{trial_id}.csv", index=False)

    return completed_trials


if __name__ == "__main__":
    typer.run(run_markertracking)
