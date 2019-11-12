import numpy as np
import xarray as xr
import logging
from utils import save_ds
logging.basicConfig(level=logging.INFO)


def theloop(arr):
	"""Generate DataArrays of ID, index, and duration of events.""" 
	out_event_size = arr.max()            # largest number of events -> defines output array size
	nz = arr.shape[1]                     # number of spatial points
	a = np.zeros((nz, out_event_size+1))  # +1 because we didn't include the zeros
	b = np.zeros((nz, out_event_size+1))
	c = np.zeros((nz, out_event_size+1))
	for loc in np.arange(nz):
		if loc % 1000 == 0:
			logging.info(f"We are up to location index {loc}")
		loc_ids, init_ndx, duration = np.unique(
	    	arr[:,loc], return_index=True, return_counts=True)
		n_loc = len(loc_ids)
		a[loc, 0:n_loc] = loc_ids
		b[loc, 0:n_loc] = init_ndx
		c[loc, 0:n_loc] = duration
		# a: the individual id numbers for events at each point
		# b: the index of the first occurrence of each event (initial time)
		# c: the number of values with the id value, i.e., the duration in days
	return a,b,c


def run(indata):
    """indata: event detection DataArray or DataSet"""
 
    if isinstance(indata, xr.DataArray):
    	events = indata
    else:
    	events = indata["Event_ID"]

    logging.info("events array defined.")

    # turn events into time x space by stacking lat & lon:
    events_stacked = events.stack(z=("lat", "lon"))
    logging.info("Stacked events.")
    # events_stacked is [time, z]

    # make sure to only have integers for the event IDs:
    zint = events_stacked.values.astype(int)
    logging.info(f"Convert events to integers. Result is shape {zint.shape}.")  # should still be [time, z]

    mx = np.max(zint)
    logging.info(f"Max number of events is {mx}; output dimesion size (add one for zeros).")

    ids, ndx, dur = theloop(zint)
    logging.info("Loop done.")

    # use ndx to go back to 'time' and construct array of datetimes
    dates = np.full(ndx.shape, indata.time[0])
    for loc in np.arange(ndx.shape[0]):
        dates[loc, :] = indata.time[ndx[loc, :]]
    dates[:, 1:] = np.where(ndx[:, 1:] == 0, np.nan, dates[:, 1:]) # in case 0 is actually part of event

    # Convert resulting numpy arrays to Xarray DataArrays 
    ids_da = xr.DataArray(ids, coords={"z":events_stacked['z'], 'events':np.arange(1,mx+2)}, 
    	dims=("z", "events"))
    ndx_da = xr.DataArray(ndx, coords={"z":events_stacked['z'], 'events':np.arange(1,mx+2)}, 
    	dims=("z", "events"))
    cnt_da = xr.DataArray(dur, coords={"z":events_stacked['z'], 'events':np.arange(1,mx+2)}, 
    	dims=("z", "events"))
    dates_da = xr.DataArray(dates, coords={"z":events_stacked['z'], 'events':np.arange(1,mx+2)},
        dims=("z", "events"))
    ids_da.name = "Event_ID"
    ndx_da.name = "initial_index"
    cnt_da.name = "duration"
    dates_da.name = 'initial_date'

    logging.info("DataArray are made")
    ids_da = ids_da.unstack()
    ndx_da = ndx_da.unstack()
    cnt_da = cnt_da.unstack()
    dates_da = dates_da.unstack()
    logging.info("Unstacked.")

    return xr.merge([ids_da, ndx_da, cnt_da, dates_da])
    

if __name__ == "__main__":
    #
    # debug/testing options:
    #
    testing = True
    test_sample_size = 5*366
    # load event_IDs
    # observed Tmax
    # fil = (
    #     "/project/amp/brianpm/TemperatureExtremes/Derived/CPC_tmax_90pct_event_detection.nc"
    # )
    # model TREFMX
    fil = "/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_detection.nc"
    ds = xr.open_dataset(fil)
    logging.info("ds is defined.")

    # go do the work
    ds_out = run(ds)
    
    # Save the result in a netCDF file
    if not testing:
        output_file = "/project/amp/brianpm/TemperatureExtremes/Derived/f.e13.FAMIPC5CN.ne30_ne30.beta17.TREFMXAV.90pct_event_attributes.nc"
        save_ds(ds_out, output_file)    
    logging.info("DONE.")