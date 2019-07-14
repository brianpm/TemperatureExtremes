import xarray as xr
import numpy as np

# function that does the counting logic


def incrementer(current_value, previous_value, last_id):

    # function that does the counting logic

    if current_value == 1:
        if previous_value > 0:
            return last_id  # continue current event
        else:
            return last_id + 1  # start a new event
    else:
        return 0  # non-event


# this makes incrementor work on numpy arrays:
vincrementer = np.vectorize(incrementer)

# the testing data set:
# "by_coords" for newest version of xarray
ds = xr.open_mfdataset("/project/amp/akwilson/2006-2019/tmax.*.nc", combine="by_coords")

# the quantiles:
ds_q = xr.open_dataset(
    "/project/amp/brianpm/TemperatureExtremes/Derived/CPC_tmax_dayofyear_quantiles_15daywindow_c20190622.nc"
)

tmax = ds["tmax"]

ninety = ds_q["tmax"].sel(quantile=0.9)
# make 'dayofyear' be the coordinate variable for ninety
ninety = ninety.rename({"time": "dayofyear"})
ninety["dayofyear"] = np.arange(1, 367)

# now make an array that equals 1 when tmax >= 90p, 0 otherwise
extreme_mask = np.where(tmax.groupby("time.dayofyear") >= ninety, 1, 0)
# get it into form of DataArray with coordinates
xmask = xr.DataArray(extreme_mask, coords=tmax.coords, dims=tmax.dims)

# make an array that is shape lat x lon, filled with zeros
# this will hold the current number of events at each location
xcount = np.zeros((360, 720))

# initialize a new array:
event_id = np.zeros(tmax.shape)
event_id[0, ...] = extreme_mask[0, ...]

# go through the all the times in the data:
# event_id will get filled in with 0 (non-event points) or
# an integer that should identify the event number
# This will be at each grid point:
# ---> so each point should have its own event sequence that is independent from other locations
# This loop will be slow; there might be ways to improve it, but we can suffer the wait for now.
for t in np.arange(1, len(tmax["time"])):
    event_id[t, ...] = vincrementer(xmask[t, ...], xmask[t - 1, ...], xcount)
    # increment xcount:
    # rule: if the current event_id is larger than the last time, it means we started a new event,
    #       so increment xcount, otherwise keep the current value.
    xcount = np.where(event_id[t, ...] > event_id[t - 1, ...], xcount + 1, xcount)

# make event_id into a proper DataArray:
event_id_da = xr.DataArray(event_id, coords=tmax.coords, dims=tmax.dims)
event_id_da.name = "Event_ID"
event_id_da.attrs["long_name"] = "Event ID Number based on Tmax > 90th percentile"

# option -- should we save this as a dataset:
if save_out:
    event_id_da.to_netcdf(
        OUTPUT,
        format="NETCDF4",
        encoding={event_id_da.name: {"zlib": True, "_FillValue": None}},
    )
