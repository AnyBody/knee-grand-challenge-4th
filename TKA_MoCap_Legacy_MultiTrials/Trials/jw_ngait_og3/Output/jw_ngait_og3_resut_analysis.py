import numpy as np    
import scipy as sp
import pandas as pd
import re   
import matplotlib.pyplot as plt
import glob
import os
import math
from sklearn.metrics import r2_score

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
list_linestyles = ['-', '--', '-.', ':']*100

list_files_h5 = glob.glob('.\*.h5')

str_name_folder_trial = os.path.abspath(os.pardir).split("\\")[-1]

h5file = h5py2.File(list_files_h5[0], 'r+') 

Tarr = np.array(h5file['Output.Abscissa.t'])
Carr = (Tarr - Tarr[0])/(Tarr[-1] - Tarr[0])*100
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
        
df_mus_act = pd.DataFrame.from_dict(dict_mus_act).assign(Cycle = Carr).set_index('Cycle')
df_mus_force = pd.DataFrame.from_dict(dict_mus_force).assign(Cycle = Carr).set_index('Cycle')
df_contact = pd.DataFrame.from_dict(dict_contact).assign(Cycle = Carr).set_index('Cycle')

for mus_group_name in list_mus_group_names:
    list_target_mus_names = [x for x in list_mus_names if x.startswith(mus_group_name)]
    df_mus_group_act = df_mus_act[list_target_mus_names]
    df_mus_group_force = df_mus_force[list_target_mus_names]
    dict_df_mus_act[mus_group_name] = df_mus_group_act
    dict_df_mus_force[mus_group_name] = df_mus_group_force


contact_force_sum_calculated_max = np.max(df_contact[['F_sum_calculated']].max())
print('Maximum contact force(N):', contact_force_sum_calculated_max)

contact_force_BW_ratio_sum_calculated_max = np.max(df_contact[['BW_ratio_F_sum_calculated']].max())
print('Maximum contact force B Wratio:', contact_force_BW_ratio_sum_calculated_max)
fig_cnt = 0
        
df_contact_lateral_absolute = df_contact[['F_lateral_calculated', 'F_lateral_measured']]
plt.figure(num=fig_cnt)
df_contact_lateral_absolute.plot(grid=True)
plt.title('Contact Force: Lateral', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('Force(N)')
plt.ylim(0, math.ceil(contact_force_sum_calculated_max/1000)*1000)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force Lateral', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1

df_contact_medial_absolute = df_contact[['F_medial_calculated', 'F_medial_measured']]
plt.figure(num=fig_cnt)
df_contact_medial_absolute.plot(grid=True)
plt.title('Contact Force: Medial', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('Force(N)')
plt.ylim(0, math.ceil(contact_force_sum_calculated_max/1000)*1000)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force Medial', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1


df_contact_sum_absolute = df_contact[['F_sum_calculated', 'F_sum_measured']]
plt.figure(num=fig_cnt)
df_contact_sum_absolute.plot(grid=True)
plt.title('Contact Force: Total', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('Force(N)')
plt.ylim(0, math.ceil(contact_force_sum_calculated_max/1000)*1000)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force Total', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1

df_contact_lateral_ratio = df_contact[['BW_ratio_F_lateral_calculated', 'BW_ratio_F_lateral_measured']]
plt.figure(num=fig_cnt)
df_contact_lateral_ratio.plot(grid=True)
plt.title('Contact Force BW Ratio: Lateral', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('BW ratio')
plt.ylim(0, 4)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force BW Ratio Lateral', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1

df_contact_medial_ratio = df_contact[['BW_ratio_F_medial_calculated', 'BW_ratio_F_medial_measured']]
plt.figure(num=fig_cnt)
df_contact_medial_ratio.plot(grid=True)
plt.title('Contact Force BW Ratio: Medial', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('BW ratio')
plt.ylim(0, 4)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force BW Ratio Medial', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1

df_contact_sum_ratio = df_contact[['BW_ratio_F_sum_calculated', 'BW_ratio_F_sum_measured']]
plt.figure(num=fig_cnt)
df_contact_sum_ratio.plot(grid=True)
plt.title('Contact Force BW Ratio: Total', loc='center')
plt.xlabel('Cycle(%)')
plt.ylabel('BW ratio')
plt.ylim(0, 4)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)    
plt.savefig(str_name_folder_trial+'_Contact Force BW Ratio Total', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+=1

list_mus_group_knee_flexor_names = ['GastrocnemiusMedialis', 'GastrocnemiusLateralis', 'BicepsFemorisCaputLongum', 'BicepsFemorisCaputBreve', 'Gracilis', 
                                    'Plantaris', 'Popliteus', 'Sartorius', 'Semimembranosus', 'Semitendinosus']
list_mus_knee_flexor_names = [x for x in list_mus_names for y in list_mus_group_knee_flexor_names if x.startswith(y)]
list_mus_group_knee_extensor_names = ['RectusFemoris', 'VastusIntermedius', 'VastusLateralisInferior', 'VastusLateralisSuperior',  
                                    'VastusMedialisInferior', 'VastusMedialisMid', 'VastusMedialisSuperior']
list_mus_knee_extensor_names = [x for x in list_mus_names for y in list_mus_group_knee_extensor_names if x.startswith(y)]

df_mus_force_knee_flexor = pd.concat([df_contact[['F_lateral_calculated']], df_mus_force[list_mus_knee_flexor_names]], sort=True)
plt.figure(num=fig_cnt)
df_mus_force_knee_flexor.plot(grid=True, style=list_linestyles)
plt.title('Contact Force vs Knee Flexors Muscle Forces')
plt.xlabel('Cycle(%)')
plt.ylabel('Force(N)')
#plt.ylim(0, math.ceil(contact_force_sum_calculated_max/1000)*1000)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)
plt.savefig(str_name_folder_trial+'_Knee Flexors Muscle Forces', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+1

df_mus_force_knee_extenstor = pd.concat([df_contact[['F_lateral_calculated']], df_mus_force[list_mus_knee_extensor_names]], sort=True)
plt.figure(num=fig_cnt)
df_mus_force_knee_extenstor.plot(grid=True, style=list_linestyles)
plt.title('Contact Force vs Knee Extensors Muscle Forces')
plt.xlabel('Cycle(%)')
plt.ylabel('Force(N)')
#plt.ylim(0, math.ceil(contact_force_sum_calculated_max/1000)*1000)
lgd=plt.legend(bbox_to_anchor=(1, 1), loc=0)
plt.savefig(str_name_folder_trial+'_Knee Extensors Muscle Forces', dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
plt.show()
plt.close(fig_cnt)
fig_cnt+1

#for mus_group_name in list_mus_group_names:
#    plt.figure(num = fig_cnt)
#    df_mus_force_temp = pd.concat([df_contact[['F_lateral_calculated']], dict_df_mus_force[mus_group_name]])
#    df_mus_force_temp.plot(grid=True, style=list_linestyles)
#    plt.title('Muscle Force: ' + mus_group_name)
#    plt.xlabel('Time(sec)')
#    plt.ylabel('Force(N)')
#    plt.grid(which='major', axis='both')
#    lgd=plt.legend(bbox_to_anchor=(1, 1), loc=2)
#    plt.show()
#    plt.close(fig_cnt)
#    fig_cnt+1

h5file.close()
    
arr_BW_ratio_F_lateral_calculated = np.array(df_contact['BW_ratio_F_lateral_calculated'])
arr_BW_ratio_F_lateral_measured = np.array(df_contact['BW_ratio_F_lateral_measured'])
pearson_corr_F_lateral = sp.stats.pearsonr(arr_BW_ratio_F_lateral_calculated, arr_BW_ratio_F_lateral_measured )
RMSE_F_lateral = np.sqrt(((arr_BW_ratio_F_lateral_calculated - arr_BW_ratio_F_lateral_measured)**2).mean())
print("Pearson Correlation F lateral = ", pearson_corr_F_lateral)
print("RMSE F lateral BW ratio = ",  RMSE_F_lateral)

arr_BW_ratio_F_medial_calculated = np.array(df_contact['BW_ratio_F_medial_calculated'])
arr_BW_ratio_F_medial_measured = np.array(df_contact['BW_ratio_F_medial_measured'])
pearson_corr_F_medial = sp.stats.pearsonr(arr_BW_ratio_F_medial_calculated, arr_BW_ratio_F_medial_measured )
RMSE_F_medial = np.sqrt(((arr_BW_ratio_F_medial_calculated - arr_BW_ratio_F_medial_measured)**2).mean())
print("Pearson Correlation F medial = ", pearson_corr_F_medial)
print("RMSE F medial BW ratio = ",  RMSE_F_medial )

arr_BW_ratio_F_sum_calculated = np.array(df_contact['BW_ratio_F_sum_calculated'])
arr_BW_ratio_F_sum_measured = np.array(df_contact['BW_ratio_F_sum_measured'])
pearson_corr_F_sum = sp.stats.pearsonr(arr_BW_ratio_F_sum_calculated, arr_BW_ratio_F_sum_measured )
RMSE_F_sum = np.sqrt(((arr_BW_ratio_F_sum_calculated - arr_BW_ratio_F_sum_measured)**2).mean())
print("Pearson Correlation F sum = ", pearson_corr_F_sum)    
print("RMSE F sum BW ratio = ",  RMSE_F_sum )

