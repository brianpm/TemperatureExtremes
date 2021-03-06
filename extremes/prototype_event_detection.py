import logging
import xarray as xr
import numpy as np
try:
    from tqdm import tqdm
except ImportError:
    import getpass
    print(f"{getpass.getuser()}, you were supposed to install tqdm!")
    def tqdm(*args):
        return args[0]

from utils import save_ds
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

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


def _run(ds, ds_q, var_name):
    """Use quantile value to define threshold value to detect events.
       ds:  the DataSet with original data
       ds_q: the DataSet with the quantile values
       var_name: the variable name in ds AND ds_q
    """

    # ds could be a DataArray:
    if isinstance(ds, xr.DataArray):
        tmax = ds.astype('float32')
    else:
        tmax = ds[var_name].astype('float32')  # reduce to float32 to allow large arrays

    if isinstance(ds_q, xr.DataArray):
        ninety = ds_q.sel(quantile=0.9)
    else:
        ninety = ds_q[var_name].sel(quantile=0.9)

    # make 'dayofyear' be the coordinate variable for ninety
    ndaysperyear = len(ds_q['time'])
    ninety = ninety.rename({"time": "dayofyear"})
    ninety["dayofyear"] = np.arange(1, ndaysperyear+1)
    logging.info(f"Made array ninety, {ninety.shape}")

    # now make an array that equals 1 when tmax >= 90p, 0 otherwise
    extreme_mask = np.where(tmax.groupby("time.dayofyear") >= ninety, np.int8(1), np.int8(0))
    logging.info(f"Made the mask. It is shape: {extreme_mask.shape} It is type: {extreme_mask.dtype}")
    # get it into form of DataArray with coordinates
    xmask = xr.DataArray(extreme_mask, coords=tmax.coords, dims=tmax.dims)
    logging.info(f"xmask created, has dtype {xmask.dtype} and shape {xmask.shape}")
    # make an array that is shape lat x lon, filled with zeros
    # this will hold the current number of events at each location
    xshape = tmax.shape # assume it is time, lat, lon
    assert(len(xshape) == 3)
    nlat = xshape[1]
    nlon = xshape[2]
    xcount = np.zeros((nlat, nlon), dtype=np.uint32)

    # initialize a new array:
    event_id = np.zeros(xshape, dtype=np.uint32)
    event_id[0, ...] = extreme_mask[0, ...]

    # go through the all the times in the data:
    # event_id will get filled in with 0 (non-event points) or
    # an integer that should identify the event number
    # This will be at each grid point:
    # ---> so each point should have its own event sequence that is independent from other locations
    # This loop will be slow; there might be ways to improve it, but we can suffer the wait for now.
    for t in tqdm(np.arange(1, len(tmax["time"])), desc="Time Loop"):
        event_id[t, ...] = vincrementer(xmask[t, ...], xmask[t - 1, ...], xcount)
        # increment xcount:
        # rule: if the current event_id is larger than the last time, it means we started a new event,
        #       so increment xcount, otherwise keep the current value.
        xcount = np.where(event_id[t, ...] > event_id[t - 1, ...], xcount + 1, xcount)

    # make event_id into a proper DataArray:
    event_id_da = xr.DataArray(event_id, coords=tmax.coords, dims=tmax.dims)
    event_id_da.name = "Event_ID"
    event_id_da.attrs["long_name"] = "Event ID Number based on Tmax > 90th percentile"

    return event_id_da


if __name__ == "__main__":
    # the testing data set:
    # "by_coords" for newest version of xarray

    # OBSERVED TMAX
    # ds = xr.open_mfdataset("/project/amp/jcaron/CPC_Tminmax/tmax.*.nc", combine="by_coords")

    # MODEL TMAX:
    data_ds = xr.open_dataset("/project/amp/brianpm/TemperatureExtremes/Regridded/f.e13.FAMIPC5CN.ne30_ne30.beta17.t3.cam.h1.TREFMXAV.19650101-20051231.regrid.nc")

    # the quantiles:
    quant_ds = xr.open_dataset(
        "/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.dayofyear_quantiles_15daywindow_c20190626.nc"
    )

    ndaysperyear = 365 # Model => 365, Obs => 366

    varname = "TREFMXAV"

    event_id_da = _run(data_ds, quant_ds, varname)

    # option -- should we save this as a dataset:
    save_out = True
    OUTPUT = "/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_detection.nc"
    if save_out:
        save_ds(event_id_da, OUTPUT)

