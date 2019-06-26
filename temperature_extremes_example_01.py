# import matplotlib
# matplotlib.use('PS') 
import numpy as np 

import xarray as xr

import matplotlib.pyplot as plt

import cartopy.crs as ccrs 

ds = xr.open_mfdataset("/project/amp/jcaron/CPC_Tminmax/tmax.*.nc") 
# ^-- this is how we open a multi-file dataset using xarray. It can take a glob pattern or a list of files. Order of that list matters, as xarray does not re-order based on the netCDF record dimension.


# what data variables are available:
print(f"The {len(list(ds.data_vars))} variables in this dataset are {ds.data_vars}")
# ^-- this is an "f-string" which is "formatted string"; you need python 3.6 (I think) to use it, but it is a great feature and I highly recommend it. 


# what if we need to know the variables and the units:
[print(f"{ds[i].name} has units of {ds[i].attrs['units']}") for i in ds.data_vars]
# ^-- this is called a list comprehension; it is a short-hand way to write a loop that returns a list.

# get out the Tmax data:
tmax = ds['tmax'].compute()  # note: I add the compute method to force the DataArray into memory here.  

# say we want to know the average maximum temperature in each month
tmax_avg_by_month = tmax.groupby('time.month').mean(dim='time')
# here we have used two different methods on the xarray DataArray object:
# a. groupby is a convenience feature that knows how to deal with time coordinates (under good conditions)
#    It will create a groupby object that would have dimensions of ('time', 'month', lat, lon)
#    such that all the times that fall within each of the 12 months are grouped into the time dimension
# b. mean(dim='time') then just says let's average all the times, leaving (month, lat, lon)
# check the result
print(tmax_avg_by_month)

# Now let's go ahead and make a figure showing each month

# some preliminaries:
month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
lons, lats = np.meshgrid(ds['lon'], ds['lat'])  # this creates arrays of longitude and latitude

fig, ax = plt.subplots(figsize=(12,12), nrows=3, ncols=4, subplot_kw={"projection":ccrs.Robinson()}, constrained_layout=True)

for i, a in enumerate(ax.ravel()):
    im = a.contourf(lons, lats, tmax_avg_by_month.isel(month=i), transform=ccrs.PlateCarree(), cmap='inferno_r')
    a.coastlines()
    cbar = fig.colorbar(im, ax=a, shrink=0.5, orientation='horizontal')
    # reduce ticks:
    clr_ticks = cbar.get_ticks()
    cbar.set_ticks(clr_ticks[::2])  
    # make the map global rather than have it zoom in to
    # the extents of any plotted data
    a.set_global()
    a.set_title(month_names[i], loc='left', fontsize=10)




fig.savefig("/project/amp/brianpm/plots/tempextremes/test_figure_001.pdf")

