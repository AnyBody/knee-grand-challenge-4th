from pathlib import Path

from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, OperationRun, Dump
#import typer
import numpy as np
import os

def run_inversedynamics(mainfiles: list[Path], create_video: bool, **kwargs) -> list[Path]:


    if not mainfiles: 
        print("No trials found.")
        return []


    # Ignore any errors from reading in static reference files which
    # contain marker positions which are not in the dynamic trials.
    ignore_errors = ["static_ref.anyset"]
    timevar = "Main.Studies.InverseDynamicStudy.Output.Abscissa.t"
    interpvar = "Main.Studies.InverseDynamicStudy.Output.GaitCycle.Abscissa"
    trialid = "Main.ModelSetup.TrialSpecificData.TrialID"
    subjectid = "Main.ModelSetup.SubjectSpecificData.SubjectID"
    trialtype = "Main.ModelSetup.TrialSpecificData.TrialType"
    outputfolders = [
        "Main.Studies.InverseDynamicStudy.Output.Outputs_Muscles",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_JCF",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_ASC",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_JointAngles",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_JointVel",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_JointMoments",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_JointReactionMoments",
        "Main.Studies.InverseDynamicStudy.Output.Outputs_KneeCondyleForces",
    ]

    macros = []
    for mainfile in mainfiles:
        macro = [
            Load(mainfile),
            OperationRun("Main.RunParameterIdentification"),
            OperationRun("Main.RunAnalysis<<<<<<<<<<<<<<"),
            #OperationRun("Main.RunAnalysis.<LoadParameters"),
            #OperationRun("Main.Studies.InverseDynamicStudy.InverseDynamics"),
            #Dump("Main.Studies.InverseDynamicStudy.Output.MaxMuscleActivity"),
            # Dump(timevar),
            # Dump(interpvar),
            # Dump(trialid),
            # Dump(subjectid),
            # Dump(trialtype),    
            # *(Dump(f) for f in outputfolders),
        ]
        if create_video:
            macro = [
                macro[0],
                OperationRun("Main.Studies.InverseDynamicStudy.VideoTool.Create_Video"),
                Dump(timevar),
            ]
        
        macros.append(macro)

    app = AnyPyProcess(ignore_errors=ignore_errors, return_task_info=False, **kwargs)

    #logfile = Path("logs/inversedynamics.txt").absolute()
    # #typer.echo(f"Running {len(mainfiles)} trial(s)...")

    results = app.start_macro(macros)#, logfile=logfile)

    # completed_trials = []
    # for i, result in enumerate(results):
    #     if result['task_processtime'] == 0:
    #         continue
    #     if 'ERROR' in result or timevar not in result:
    #         if log:=result.get("task_logfile"):
    #            print(f"Failed: {mainfiles[i].relative_to(Path.cwd())} ( [blue]{log}[/blue] )")
    #         continue

    #     completed_trials.append(mainfiles[i])

    #     if create_video:
    #         # No need to export data
    #         continue

    #     df = result.to_dataframe(
    #         index_var=timevar,
    #         # interp_var=interpvar,
    #         # interp_val=np.linspace(0, 100, 101),
    #     )

    #     # Drop columns containing "..." (from dumping folders from AnyBody)
    #     # and shorten column names
    #     df = df.loc[:, df.iloc[0] != "..."]
    #     df = df.loc[:, ~df.columns.str.startswith("task_")]

    #     df.columns = df.columns.str.replace("Main.ModelSetup.SubjectSpecificData.", "")
    #     df.columns = df.columns.str.replace("Main.ModelSetup.TrialSpecificData.", "")
    #     df.columns = df.columns.str.replace(timevar, "t")
    #     df.columns = df.columns.str.replace(interpvar, "gait_cycle")
    #     df.columns = df.columns.str.replace("Main.Studies.InverseDynamicStudy.Outputs_", "")

    #     # Trim all data outside events (gait_cycle outside range [0, 100])
    #     df = df[(df["gait_cycle"] >= 0) & (df["gait_cycle"] <= 100)]

    #     trialid = df["TrialID"].iloc[0]
    #     subject_id = df["SubjectID"].iloc[0]

    #     outputfolder = Path("Results/inversedynamics")
    #     outputfolder.mkdir(parents=True, exist_ok=True)
        
    #     df.to_csv(outputfolder / f"{subject_id}_{trialid}.csv", index=False)

    return results


if __name__ == "__main__":
    import os

    # Save the original working directory
    original_cwd = Path.cwd()
    target_dir = original_cwd / "Studies" / "AAU-MRI" / "Subjects"

    # Change to the target directory
    os.chdir(target_dir)
    print(f"Changed working directory to: {target_dir}")

    # Parse and print subdirectories (2 levels)
    subdirs = [p for p in Path.cwd().glob("*/Trials Dynamic/*") if p.is_dir()]
    print("Subdirectories (2 levels):")
    models = [str(d)+"/main.dev.any" for d in subdirs]
    run_inversedynamics(mainfiles=models, create_video=False)

    # Return to the original working directory
    os.chdir(original_cwd)
    print(f"Returned to original directory: {original_cwd}")
