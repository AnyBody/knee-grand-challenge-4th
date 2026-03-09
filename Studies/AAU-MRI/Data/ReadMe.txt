This data folder is orgnanized like this:

\[a patient folder]
    \*.stl (femurR, tibiaR,pelvisR, pelvisL, patellaR) #or left
\[c3d files folder]
    \c3d files for each patient

It can be configured using 'name_dict' variable in setup_trials.py.
name_dict will be containt entries with the following meaning: 
        patientid: [c3d_file, stl_folder, sim_start, sim_end, ref_start, ref_end, body_height, body_mass]

To generate a list of trials please run:
pixi install
pixi run python setup_trials.py

This script will prepare simulations folder. 