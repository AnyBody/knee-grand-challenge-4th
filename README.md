> **Warning**
> This repository is has not yet been updated to work with newer versions of AnyBody Modeling System and Body models (AMMR). This work is on going. 


<img src="https://github.com/AnyBody/ammr/raw/master/Docs/_static/AMMR_Logo2.png" align="right" />

# AnyBody FDK knee model
> based on the 4th year Grand Challenge dataset

This is an implementaiton of the dtailed knee model based on the dataset from the "*Grand Challenge Competition to Predict In-Vivo Knee Loads*". 
An annual competition hosted at the ASME conference for researchers to blindly predict knee loads with musculskeletal models.

THis model implementation was based on the is based on the 4th year dataset.


### Details on files/folders and model structure

1. `libdef.any` file will use an external libdef.any file which is assumed to be located in the directory up one level.
    And this external libdef.any file should include the real libdef.any from an AMMR repository that you may want to use.
    This model will work in the AMMMR version AMMR 2.2

2. The `Input/` folder contains several input dataset from the 4th competition of  the Grand Challenge Competition to Predict
   In Vivo Knee Loads (https://simtk.org/projects/kneeloads) including the STL files for both bone and implant geometries as 
   well as the motion capture data of patient trials in form of C3D files. Of course there are other related files that are 
   created and managed by AnyBody Technology A/S.

3. The `Commons` folder contains all common AnyScript files that are used for different models, especially related to the 
   customization of the human model in terms of bone scaling, muscle strength adjustment and ligament configuration.

4. The `ScalingTest` folder contains some test models where you can see how custom scaling of AMMR  TLEM2.0 bones can be applied 
   to the patient-specific geometries of the Grand Challenge Competition to Predict In Vivo Knee Loads.

5. The `TKA_Squat` folder contains a sample squat model. The purpose of this model is to illustrate the procedure of 
   patient-specific scaling of the latest AMMR human model using the dataset from the Grand Challenge Competition to Predict In 
   Vivo Knee Loads. Also this model can demonstrate how the FDK knee simulation may work by detailed modeling of the knee structure
   including implant surface contacts, ligaments and muscles.

6. The `TKA_AnyMoCap_MultiTrials` folder contains a simulation framework based on the AnyMoCap model. In this framework you can
   handle many different trials of a subject.

7. `TKA_MoCap_Legacy_MultiTrials`folder contains a simulation framework beased on the old legacy MoCap model from previous AMMR versions.
