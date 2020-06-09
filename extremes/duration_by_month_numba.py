# for numbers
import xarray as xr
import numpy as np
import pandas as pd

# # for figures
# import matplotlib as mpl
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs

from numba import jit, prange

from utils import save_ds


@jit
def my_isin(arr, test_elements):
    asiz = arr.shape[0]
    result = []
    for i in range(asiz):
        a = arr[i]
        for b in test_elements:
            if a == b:
                result.append(i)
    return sorted(result)


@jit(nopython=True, parallel=True)
def get_vals(a, b, c, d):
    s = a.shape
    out = np.empty(s[1])  # just space -- Numba can't deal with "ragged" arrays
    for i in prange(s[1]):
        temp1 = np.unique(b[:, i])
        if len(temp1) > 1:
            temp2a = my_isin(d[:, i], temp1)  # returns a list of indices
            # numba wont' let me index with a list, so we have to break it down:
            tmp2b = [c[j, i] for j in temp2a]  # makes a list of values from 'c'
            tmp2c = 0
            for k in tmp2b:
                tmp2c += k
            out[i] = tmp2c / len(tmp2b)
        #             out[i] = temp2.mean()
        else:
            out[i] = np.nan
    return out


if __name__ == "__main__":

    # Attribute
    stem = "/project/amp/brianpm/TemperatureExtremes/Derived/"
    # fil = "CPC_tmax_90pct_event_attributes_compressed.nc"
    fil = "f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_attributes_compressed.nc"

    ds = xr.open_dataset(stem + fil)
    ds_stack = ds.stack(z=("lat", "lon"))

    evalues = ds_stack["Event_ID"].values
    dvalues = ds_stack["duration"].values

    # Detection
    # ds_events = xr.open_dataset(stem + "CPC_tmax_90pct_event_detection.nc")
    ds_events = xr.open_dataset(stem + "f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_detection.nc")
    events = ds_events["Event_ID"]  # [time, lat, lon]
    events_a = np.where(events.values > 0, events.values, np.nan)  # exclude zeros
    events_a = xr.DataArray(events_a, coords=events.coords, dims=events.dims)
    ev = events_a.stack(z=("lat", "lon"))  # (time, z)

    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    mean_duration_xr = dict()
    for month in months:
        select_month = months[month]
        ev_month = ev[
            ev["time.month"] == select_month, :
        ]  # (time*, z), time* is only the times in august
        mean_duration = get_vals(ev.values, ev_month.values, dvalues, evalues)
        mean_duration_xr[month] = xr.DataArray(
            mean_duration, coords={"z": ds_stack["z"]}, dims=("z",)
        ).unstack()
    out_data = xr.concat(mean_duration_xr.values(), dim="month")
    out_data.name = "mean_duration"
    out_data.coords['month'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    out_ds = out_data.to_dataset()
    save_ds(
        out_ds,
        "/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_mean_duration.nc",
    )

# Performance in production:
# CPC Tmax:
# topaz.cgd.ucar.edu$ time python duration_by_month_numba.py
# real    5m10.791s
# user    202m54.117s
# sys 0m40.830s
#
# CESM1 regridded TREFMXAV:
#