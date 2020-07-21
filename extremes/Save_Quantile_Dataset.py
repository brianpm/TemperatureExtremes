# coding: utf-8
import numpy as np 
import xarray as xr
from datetime import date
import multiprocessing as mp
import logging
from utils import save_ds
try:
    from tqdm import tqdm
except ImportError:
    import getpass
    print(f"{getpass.getuser()}, you were supposed to install tqdm!")
    def tqdm(*args):
        return args[0]
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


def _run(ds, tmax, parallel=False, ncpu=None):
    #
    # --- no more user input needed after here ---
    # --- REQUIRED: ds, tmax
    #

    time_ndx = tmax.dims.index('time')

    if 'long_name' in tmax.attrs:
        var_long_name = tmax.attrs['long_name']
    else:
        var_long_name = tmax.name

    if 'units' in tmax.attrs:
        var_units = tmax.attrs['units']
    else:
        logging.warning("NO UNITS ATTACHED TO VARIABLE.")
        var_units = "N/A"
        
    #
    # metadata / coordinates / define quantile
    #
    lat = ds['lat']
    lon = ds['lon']
    time = ds['time']
    quantile = [.01, .05, .1, .25, .5, .75, .9, .95, .99]  # TODO: make this customizable

    tmax_np = tmax.values
    logging.info("Convert to numpy array.")

    tday = time.dt.dayofyear.values # day of year for every time.
    doy = set(tday)                 # kind of silly, but will deal with 365 or 366 day year
    doy_list = list(doy)            # need a version that can be indexed.
    doy_dict = dict()
    doy_quants = dict()
    Ndays = len(doy_list)-1

    use_inds = list()  # keep indices in list for parallelization
    for i, day in enumerate(doy_list):
        logging.info(f"Working on day {i} of {Ndays}")
        use_days = get_window_indices(doy_list, i, 7, 7) # Follows Perkins & Alexander
                                                         # TODO: make window size customizable.
        use_inds.append(np.concatenate([np.nonzero(tday == j)[0] for j in use_days]))
        # doy_dict[day] = tmax_np[use_inds, ...]
        if not parallel:
            doy_quants[day] = get_our_quants(tmax_np[use_inds[-1], ...])  # taking last indices entry

    logging.info("Completed loop through days of year. Proceed with parallel is {}".format(parallel))

    xr_das = {}  # dictionary to hold quantiles for each day-of-year
    if parallel:
        max_cpu = mp.cpu_count()
        if ncpu is None:
            ncpu = max_cpu
            if ncpu > 8:
                ncpu /= 2  # don't take more than half of larger machines
        if ncpu > max_cpu:
            logging.info(f"Requested {ncpu} but only {max_cpu} available, changing.")
            ncpu = max_cpu
        logging.info(f"You should know that you are requesting {ncpu} CPUS (type of ncpu is {type(ncpu)}")
        with mp.Pool(ncpu) as p:
            ziter = (tmax_np[d, ...] for d in use_inds)
            result = list(tqdm(p.imap(get_our_quants, ziter), total=len(use_inds)))
            doy_quants = zip(doy_list, result)
        for dq in doy_quants:
            # different from non-parallel case b/c doy_quants is an iterator
            xr_das[dq[0]] = xr.DataArray(dq[1], coords={"quantile":quantile, "lat":lat, "lon":lon}, dims=("quantile", "lat", "lon"))
    else:
        # CONVERSION TO XARRAY AND EXPORT TO netCDF
        for i in doy_quants:
            xr_das[i] = xr.DataArray(doy_quants[i], coords={"quantile":quantile, "lat":lat, "lon":lon}, dims=("quantile", "lat", "lon"))

    logging.info("Day of year quantiles stored in dictionary, proceed to file writing.")         
    # doy_quants = {i: get_our_quants(doy_dict[i]) for i in doy_dict} # MEMORY ERROR (even with a lot of memory)


    xr_output = xr.concat(list(xr_das.values()), dim="time")
    output_time = xr.DataArray(np.array(doy_list), dims=["time"], attrs={"units":"day-of-year"})
    # xr_output['time'] = output_time
    xr_output.assign_coords({"time":output_time})
    xr_output.name = tmax.name
    xr_output.attrs['long_name'] = var_long_name
    xr_output.attrs['units'] = var_units
    return xr_output



if __name__ == "__main__":

    # # Calculate and save the quantiles from large data
    # 
    # (1979--2018 daily values on a 0.5� grid).
    # To increase the sample size for each calendar day, we apply a window centered on the day and extending 7 days before and after. 
    # 
    # Efficiency is a problem in this script.
    # - There is a slowdown using xarray DataArrays for the calculations,
    #   so I use xarray as I/O, but upon data import, I just get the values as a numpy array (much faster).
    # - By going to numpy, we lose 'groupby', so we have to implement basically our own version.
    # - To do the windowing around each day, we employ a nice trick using the modulo operator.
    # - Working on numpy arrays that are 15-day windows around each day makes a lot of large arrays,
    #   which becomes a major memory issue. To minimize the memory requirements, we use a generator comprehension
    #   that only gets one sub-array at a time.
    # - Although the problem at the end is embarrasingly parallel -- i.e., computing the quantiles for 366 sub-arrays --
    #   I have not been able to get an effective parallelization (making the overall run time serial and slow).
    # - Once done, we convert back to a DataArray, and the final resulting dataset is saved to a netCDF file.
    # --- Brian Medeiros, 22 June 2019 (run on topaz.cgd.ucar.edu; ~1 hr)
    #

    OUTPUT = f"/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.dayofyear_quantiles_15daywindow_c{date.today().strftime('%Y%m%d')}.nc"
    logging.info(f"YOUR OUTPUT FILE WILL BE NAMED: {OUTPUT}")

    # OBSERVATIONAL DATA:
    # gpat = "/project/amp/jcaron/CPC_Tminmax/tmax.*.nc"
    # ds = xr.open_mfdataset(gpat, decode_cf=False)
    # ds = xr.decode_cf(ds)
    # out_file_info = f"Data derived from glob patter {gpat}, resulting in data set with {len(ds['time'])} time slices."
    # tmax = ds['tmax']

    # REGRIDDED MODEL DATA:
    ds = xr.open_dataset("/project/amp/brianpm/TemperatureExtremes/Regridded/f.e13.FAMIPC5CN.ne30_ne30.beta17.t3.cam.h1.TREFMXAV.19650101-20051231.regrid.nc")
    tmax = ds['TREFMXAV']

    logging.info("Loaded the tmax DataArray (likely lazy load)")

    ds_out = _run(ds, tmax)
    save_ds(ds_out, OUTPUT)
    # xr_output.to_netcdf(OUTPUT, format='NETCDF4', encoding={tmax.name: {"zlib": True, "_FillValue": None}})
    logging.info("All done.")
