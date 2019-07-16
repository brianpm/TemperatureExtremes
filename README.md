# TemperatureExtremes
This is a repository for diagnostics of temperature extremes in climate data. For now, it focuses on analysis of daily minimum and maximum temperatures.


## Regridding Method

The spectral element files are on the unstructured mesh, so variables have coordinates of (ncol, time). For convenience, I have regridded selected files and put them in the Regridded folder in the data directory.They are regridded to the 0.5degree grid that the observations use. To do the regridding, I used the NCO command ncremap, invoked as

``` 
ncremap -4 -L 4 -m map_ne30_to_halfdegree.nc
        -s /project/amp/brianpm/TemperatureExtremes/ne30np4_091226_pentagons.nc
        -d /project/amp/jcaron/CPC_Tminmax/tmax.1980.nc
        /project/amp/brianpm/TemperatureExtremes/TSMX/f.e13.FAMIPC5CN.ne30_ne30.beta17.t3.cam.h1.TSMX.19650101-20051231.nc /project/amp/brianpm/TemperatureExtremes/Regridded/f.e13.FAMIPC5CN.ne30_ne30.beta17.t3.cam.h1.TSMX.1965\
0101-20051231.regrid.nc

```

On subsequent files, I just use the mapping file `map_ne30_to_halfdegree.nc` that is produced on the first file.

## Automated Workflow

We have developed a series of tools that can be chained together to produce data files (netCDF) and (potentially) some summary statistics and (potentially) some simple figures. 

Each script has been developed separately, and can be used independently from the others. They have been modified to be run in a prescribed order based on minimal input to a command line interface called `extreme_wf`. The input to `extreme_wf` is a YAML file and must include several pieces of information.

The workflow is very straight-forward. Call `extreme_wf` with the YAML file as the only argument. The YAML file contains all the input and output specification. Within `extreme_wf`, the YAML file is validated (i.e., it looks for required inputs) and then runs `Save_Quantile_Dataset.py` which saves a file with quantile information from the input. That file is then used in `prototype_event_detection.py` along with the input files to detect the events above the threshold quantile (right now that's the 90th percentile; see notes). The next stage is to derive the event attribute file from the event detection file using `event_attributes.py`.

It is clear that some inefficiency is built into this system if the code in `extreme_wf` does not preserve the objects being created along the way. We have modified the original scripts so that each has a `run()` method that returns an Xarray DataSet object; when the scripts are run as standalone programs, they save this dataset, and when run is called directly, `extreme_wf` is in control of saving the intermediate files (could be optional in YAML) and for providing the (in memory) dataset objects to the next step.

