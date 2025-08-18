from pathlib import Path

from anypytools import AnyPyProcess
from anypytools.macro_commands import Load, OperationRun, Dump
import typer
from rich import print


def run_staticref(mainfiles: list[Path], **kwargs) -> list[Path]:

    if not mainfiles: 
        print("No trials found.")
        return []

    macros = []
    for mainfile in mainfiles:
        macros.append(
            [
                Load(mainfile),
                OperationRun("Main.RunParameterIdentification"),
            ]
        )
    app = AnyPyProcess(**kwargs)

    logfile = Path("logs/staticref.txt").absolute()
    
    print(f"Running {len(mainfiles)} static reference trial(s)...")
    results = app.start_macro(macros, logfile=logfile)

    completed_trials = []
    for i, result in enumerate(results):
        if result['task_processtime'] == 0: 
            continue
        if 'ERROR' in result:
            if log:=result.get("task_logfile"):
              print(f"Failed: {mainfiles[i].relative_to(Path.cwd())} ( [blue]{log}[/blue] )")
            continue
        
        completed_trials.append(mainfiles[i])

    return completed_trials


if __name__ == "__main__":
    typer.run(run_staticref)
