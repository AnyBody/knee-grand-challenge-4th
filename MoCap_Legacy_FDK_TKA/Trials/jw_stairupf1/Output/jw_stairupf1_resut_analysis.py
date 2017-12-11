import numpy as np    
import scipy as sp
import pandas as pd
import re   
import matplotlib.pyplot as plt
import glob
import os

import anypytools
from anypytools import h5py_wrapper as h5py2

list_mus_names = []
list_mus_group_names = []
set_mus_group_names = set({})
dict_mus_group = {}
dict_mus_act = {}
dict_mus_force = {}
dict_contact = {}
dict_df_mus_act = {}
dict_df_mus_force = {}

list_files_h5 = glob.glob('.\*.h5')

str_name_folder_trial = os.path.abspath(os.pardir).split("\\")[-1]

h5file = h5py2.File(list_files_h5[0], 'r+') 

T = np.array(h5file['Output.Abscissa.t'])
str_mus = 'Output.BodyModel.Right.Leg.Mus'
str_contact = 'Output.Results.Contact'
list_mus_names = list(h5file[str_mus])
list_contact_names = [x for x in list(h5file[str_contact])]

for mus_name in list_mus_names:
    mus_name_modified = mus_name
    if mus_name_modified.endswith('New'):
        mus_name_modified = mus_name_modified.replace('New', '')
    if mus_name_modified[-1].isdigit():
        mus_name_modified = mus_name_modified[0:len(mus_name_modified)-1]
    if not mus_name_modified.startswith('PsoasMajor'):
        set_mus_group_names.add(mus_name_modified)

set_mus_group_names.add('PsoasMajor')        
list_mus_group_names = sorted(list(set_mus_group_names))

for item in set_mus_group_names:
    list_mus_elements = [x for x in list_mus_names if x.startswith(item)]
    dict_mus_group[item] = list_mus_elements

for mus_name in list_mus_names:
    dict_mus_act[mus_name] = np.array(h5file[str_mus+'.'+mus_name+'.Activity'])
    dict_mus_force[mus_name] = np.array(h5file[str_mus+'.'+mus_name+'.Fm'])
    
for contact_name in list_contact_names:
    dict_contact[contact_name] = np.array(h5file[str_contact+'.'+contact_name])
        
h5file.close()

df_mus_act = pd.DataFrame.from_dict(dict_mus_act).assign(Time = T).set_index('Time')
df_mus_force = pd.DataFrame.from_dict(dict_mus_force).assign(Time = T).set_index('Time')
df_contact = pd.DataFrame.from_dict(dict_contact).assign(Time = T).set_index('Time')

for mus_group_name in list_mus_group_names:
    list_target_mus_names = [x for x in list_mus_names if x.startswith(mus_group_name)]
    df_mus_group_act = df_mus_act[list_target_mus_names]
    df_mus_group_force = df_mus_force[list_target_mus_names]
    dict_df_mus_act[mus_group_name] = df_mus_group_act
    dict_df_mus_force[mus_group_name] = df_mus_group_force


fig_cnt = 0
        
df_contact_lateral_absolute = df_contact[['F_lateral_calculated', 'F_lateral_measured']]
plt.figure(num=fig_cnt)
df_contact_lateral_absolute.plot()
plt.title('Contact Force_Lateral(N)')
plt.xlabel('Time(sec)')
plt.ylabel('Force(N)')
plt.xlim([6.0, 8.0])
plt.ylim([0.0, 1500.0])
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=2)    
plt.savefig(str_name_folder_trial+'_Contact Force_Lateral(N)', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
fig_cnt+=1

df_contact_medial_absolute = df_contact[['F_medial_calculated', 'F_medial_measured']]
plt.figure(num=fig_cnt)
df_contact_medial_absolute.plot()
plt.title('Contact Force_Medial(N)')
plt.xlabel('Time(sec)')
plt.ylabel('Force(N)')
plt.xlim([6.0, 8.0])
plt.ylim([0.0, 1500.0])
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=2)    
plt.savefig(str_name_folder_trial+'_Contact Force_Medial(N)', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
fig_cnt+=1

contact_force_calculated_max = np.max(df_contact[['F_lateral_calculated', 'F_medial_calculated']].max())
print('Maximum contact force(N):', contact_force_calculated_max)

#for mus_group_name in list_mus_group_names:
#    plt.figure(num = fig_cnt)
#    dict_df_mus_act[mus_group_name].plot()
#    plt.title('Muscle Activation: ' + mus_group_name)
#    plt.xlabel('Time(sec)')
#    plt.ylabel('Activity')
#    plt.ylim([0.0, 1.0])
#    plt.grid(which='major', axis='both')
#    lgd=plt.legend(bbox_to_anchor=(1, 1), loc=2)    
#    plt.savefig(str_name_folder_trial+'Mus_Act_'+mus_group_name, dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
#    plt.show()
#    fig_cnt+=1

#ratio_force_wrt_max = 0.1    
#for mus_group_name in list_mus_group_names:
#    mus_force_group_max = np.max(dict_df_mus_force[mus_group_name].max())
#    if mus_force_group_max >= ratio_force_wrt_max*contact_force_calculated_max: 
#        plt.figure(num = fig_cnt)
#        dict_df_mus_force[mus_group_name].plot()
#        plt.title('Muscle Force: ' + mus_group_name)
#        plt.xlabel('Time(sec)')
#        plt.ylabel('Force(N)')
#        plt.ylim([-5, 1000])
#        plt.grid(which='major', axis='both')
#        lgd=plt.legend(bbox_to_anchor=(1, 1), loc=2)    
#        plt.savefig(str_name_folder_trial+'_Mus_Force_'+mus_group_name, dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
#        plt.show()
#        fig_cnt+=1
        
