# coding: utf-8
# from distributed import Client
# client = Client()
import numpy as np 
import xarray as xr
from datetime import date
import multiprocessing as mp
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Use modulo operator (i.e., remainder) to deal with circular index.
# https://stackoverflow.com/questions/8951020/pythonic-circular-list
def get_window_indices(thing, current, look_back, look_ahead):
    """Given an iterable, thing, return the values of thing in circular slice. Go back look_back steps and
       go ahead look_ahead steps.
    """
    N = len(thing)-1
    window_inds = np.arange(-1*(look_back), look_ahead+1)
    result = []
    for w in window_inds:
        result.append(thing[(current + w) % N])
    return np.array(result)  # these are the values of thing


def get_our_quants(data):
        return np.nanquantile(data, [.01, .05, .1, .25, .5, .75, .9, .95, .99], axis=0, overwrite_input=False, interpolation='linear', keepdims=False)


# # Calculate and save the quantiles from large data
# 
# This notebook walks through the calculation of quantiles. It's based on a fairly large dataset (1979--2018 daily values on a 0.5° grid). To increase the sample size for each calendar day, we apply a window centered on the day and extending 7 days before and after. 
# 
# The main "trick" applied here is to convert from xarray to numpy array for all the calculation (much faster based on testing). The dataset is then converted back to a DataArray, and the final resulting dataset is saved to a netCDF file.


METHOD = "DOY"  # [SIMPLE, DOY]
OUTPUT = f"/project/amp/brianpm/TemperatureExtremes/CPC_tmax_dayofyear_quantiles_15daywindow_PARALLEL_c{date.today().strftime('%Y%m%d')}.nc"
logging.info(f"YOUR OUTPUT FILE WILL BE NAMED: {OUTPUT}")

gpat = "/project/amp/jcaron/CPC_Tminmax/tmax.*.nc"
ds = xr.open_mfdataset(gpat, decode_cf=False)
ds = xr.decode_cf(ds)
tmax = ds['tmax']
logging.info("Loaded the tmax DataArray (likely lazy load)")

time_ndx = tmax.dims.index('time')

if 'long_name' in tmax.attrs:
    var_long_name = tmax.attrs['long_name']
else:
    var_lon_name = tmax.name

if 'units' in tmax.attrs:
    var_units = tmax.attrs['units']
else:
    logging.warning("NO UNITS ATTACHED TO VARIABLE.")
    var_units = "N/A"
    
out_file_info = f"Data derived from glob patter {gpat}, resulting in data set with {len(ds['time'])} time slices."
#
# metadata / coordinates / define quantile
#
lat = ds['lat']
lon = ds['lon']
time = ds['time']
quantile = [.01, .05, .1, .25, .5, .75, .9, .95, .99]

tmax_np = tmax.values
logging.info("Convert to numpy array.")


tday = time.dt.dayofyear.values # day of year for every time.
doy = set(tday)  # kind of silly, but will deal with 365 or 366 day year
doy_list = list(doy) # need a version that can be indexed.
doy_dict = dict()
doy_quants = dict()
Ndays = len(doy_list)-1
use_inds = list()
for i, day in enumerate(doy_list):
    logging.info(f"Working on day {i} of {Ndays}")
    use_days = get_window_indices(doy_list, i, 7, 7) # Follows Perkins & Alexander
    use_inds.append(np.concatenate([np.nonzero(j == tday)[0] for j in use_days]))

logging.info(f"constructed the indices; size is {len(use_inds)}")

# this should keep so much from being copied to each process,
# and the use of a generator expression as the argument to map
# should also keep memory use down (?)
with mp.Pool(8) as p:
    result = p.map(get_our_quants, (tmax_np[d, ...] for d in use_inds))
    doy_quants = zip(day_list, result)

logging.info("Completed loop.")
     
# doy_quants = {i: get_our_quants(doy_dict[i]) for i in doy_dict}

xr_das = {}
for i in doy_quants:
    xr_das[i] = xr.DataArray(doy_quants[i], coords={"quantile":quantile, "lat":lat, "lon":lon}, dims=("quantile", "lat", "lon"))

xr_output = xr.concat(xr_das, dim="time")
xr_output['time'].values = np.array(doy_list)
xr_output['time']['units'] = 'day-of-year'
xr_output.name = tmax.name
xr_output.attrs['long_name'] = var_lon_name
xr_output.attrs['units'] = var_units

# SAVE OUTPUT
xr_output.to_netcdf(OUTPUT, format='NETCDF4', encoding={tmax.name: {"zlib": True, "_FillValue": None}})
logging.info("All done.")



