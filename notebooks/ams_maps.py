#!/usr/bin/env python
# coding: utf-8

# for numbers
import xarray as xr
import numpy as np
import pandas as pd

# for figures
import matplotlib as mpl
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs


# # Description of this code
# 
# We define a function called `quick_map` that is a convenience function. It needs the longitude and latitude meshes and the array of data to map. The key word argument `title` can be supplied to put a title on the map. The `**kwargs` is a dictionary of optional key word arguments that get passed into `pcolormesh`. The map defaults to the Robinson projection; we can change this if there is a projection that we like better. The colormap is not specified, so it will default, if you want to specify one, just include `cmap` in the `kwargs` dict.
# 
# The code then loads the event statistics for observations and models (2 separate files), and gets the event ID numbers (lat, lon, event).
# 
# The first figures then just make the maps of total number of events.
# 
# Then we start to explore ways to divide the events by time (e.g., by month.) I'm still working on this part.

def quick_map(lons, lats, data, title=None, **kwargs):
    f, a = plt.subplots(subplot_kw={"projection":ccrs.Robinson()})
    # pass in norm as kwarg if needed
    # norm = mpl.colors.Normalize(vmin=1979, vmax=2019)
    img = a.pcolormesh(lons, lats, data, transform=ccrs.PlateCarree(), **kwargs)
    a.set_title(title)
    f.colorbar(img, shrink=0.4)
    return f, a


# # Quick events stats
# In the `event_attributes_compressed` files, we have `Event_ID`, `initial_index`, and `duration`. These are useful for doing basic statistics of the events (defined with the 90th percentile TMAX). 
# 
# Next, we load these files, and map the total number of events.

stem = "/project/amp/brianpm/TemperatureExtremes/Derived/"
obsfil = "CPC_tmax_90pct_event_attributes_compressed.nc"
mdlfil = "f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_attributes_compressed.nc"
obs_ds = xr.open_dataset(stem+obsfil)
mdl_ds = xr.open_dataset(stem+mdlfil)

obs_ids = obs_ds['Event_ID']  # each point has a series of events that are labeled as increasing integers
mdl_ids = mdl_ds['Event_ID']

# number of events:
obs_nevents = obs_ids.max(dim='events')
mdl_nevents = mdl_ids.max(dim='events')

lons, lats = np.meshgrid(mdl_ds['lon'], mdl_ds['lat'])

# plot of number of events
norm = mpl.colors.Normalize(vmin=0, vmax=1000.)
res = {'norm':norm}
fig1, ax1 = quick_map(lons, lats, obs_nevents, title="OBSERVATIONS: Total Events", **res)
ax1.add_feature(cartopy.feature.OCEAN, zorder=100)
ax1.set_extent([-180, 180,-60, 60])

fig2, ax2 = quick_map(lons, lats, mdl_nevents, title="CESM1: Total Events", **res)
ax2.add_feature(cartopy.feature.OCEAN, zorder=100)
ax2.set_extent([-180, 180,-60, 60])


# # Events divided by month
# 
# We have the index of each event, but not the actual time. Here we show how to retrieve the actual dates of events. 
# 

# original data:
obs_data = xr.open_mfdataset("/project/amp/jcaron/CPC_Tminmax/tmax.*.nc", combine='by_coords')

def get_event_dates(time_coord, init, dur):
    start_date = time_coord[init]
    finish_date = time_coord[init+dur]
    return start_date, finish_date


s = obs_ids[:, 100, 100]
x = obs_ds['initial_index'][:,100,100]
d = obs_ds['duration'][:,100,100]

for i, event in enumerate(s):
#     print(i)
    if event == 0:
        continue
    else:
        initial = x[i].astype(int)
        duration = d[i].astype(int)
        st, fn = get_event_dates(time, initial, duration)
        print(f"start: {st.values}, end: {fn.values}")


# Now the issue is that we'd like to do this for every event.
# 
# Since we already have duration, we really just need the starting time for each event at each location. We should write this when we first calculate the attributes.

# stack spatial points so only 1-d
obs_stack = obs_ds.stack(z=("lat","lon")) 


stdata = np.zeros(obs_stack['Event_ID'].shape, dtype='datetime64[s]')
print(stdata.shape)
for j in range(len(obs_stack.events)):
    print(f"Working on event {j}")
    for i in range(len(obs_stack.z)):
        if obs_stack["Event_ID"][j, i].max() <= 0:
            stdata[j, i] = '0000-01-01'  # missing
        else:
            ndx = obs_stack['initial_index'][j, i].astype(int).item()
            stdata[j, i] = time[ndx].values

start_time = xr.DataArray(stdata, coords=obs_stack.coords, dims=obs_stack.dims)
obs_event_fil = xr.open_dataset(stem+"CPC_tmax_90pct_event_detection.nc")
mdl_event_fil = xr.open_dataset(stem+"f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_detection.nc")
print(obs_event_fil['time'].min())
print(obs_event_fil['time'].max())
print(mdl_event_fil['time'].min())
print(mdl_event_fil['time'].max())
tt = np.array([time[1000].values])



