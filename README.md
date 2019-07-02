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