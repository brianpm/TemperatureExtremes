import os
import glob
import numpy as np
import xarray as xr
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from cartopy.util import add_cyclic_point

try:
    import cftime
except ImportError:
    print(
        "Sorry, looks like cftime is not going to be loaded. Will not break functionality."
    )


def wgt_areaave_xr(data, yweight, xweight=1.0):
    """
    A xarray implementation of NCL's wgt_areaave. Preserves metadata.
    Assumes data has dims (..., ydim, xdim).
    :param data: And array-like object, assumes axis = 1 is longitude, axis = 2 is latitude (to be fixed)
    :param yweight: latitude weights, array like, same size as data's latitude axis
    :param xweight: optional longitude weight, defaults to 1.
    :return: array of weighted average over latitude and longitude.
    """
    if type(xweight) == float or type(xweight) == int:
        xlength = data.shape[-1]
        # logging.debug('xlength'+str(xlength))
        # numpy: xw = np.ones(xlength) * xweight
        xw = xr.DataArray(np.ones(xlength))
    else:
        xw = xweight
    # logging.debug(xw)
    latdim = list(data.coords).index("lat")
    londim = list(data.coords).index("lon")

    # normalized weights:
    ywnorm = yweight / yweight.sum()
    xwnorm = (
        xw / xw.sum()
    )  ##**** CHECK WHETHER mfdataset makes gw(time,lat) break this method.

    xdimname = data.dims[-1]
    ydimname = data.dims[-2]

    # apply average in each direction:
    if not (xw == 1).all().values.all():
        a = (data * xwnorm).sum(dim=xdimname)
    else:
        # just apply a regular mean
        a = data.mean(dim=xdimname)

    a = (a * ywnorm).sum(dim=ydimname)
    return a


def calc_lat_weight(lat):
    return np.cos(np.radians(lat))


def get_cesm_weight(ds):
    """
    Get latitude weights for CESM data set.
    :param ds: and xr dataset (or dataarray)
    :return: weights(lat). Will try to use gw variable and correct for multifile datasets. If not there, then cos(lat) as np array.
    """
    # latitude weighting:
    if "gw" in ds:
        gw = ds["gw"]
        # if it comes out 2d things get broken.
        if any([x == "time" for x in gw.dims]):
            print("We have a time,lat version of gw. Fixing.")
            gw = gw.isel(time=0, drop=True)
    else:
        gw = calc_lat_weight(ds["lat"])  # metadata will be preserved, so slice is okay
    return gw


def global_average(fld, gw):
    """
    Calculate the global average.
    :param fld: Array-like with named dimensions and a "mean" method (i.e. xarray).
    :param gw: Weights.
    :return: Global average; performs time-average if there is a time dimension.
    """
    if "time" in fld.dims:
        return wgt_areaave_xr(fld, gw).mean(dim="time")
    else:
        return wgt_areaave_xr(fld, gw)


# TODO: Investigate method to use operator module to generalize get_sumvar and get_diffvar.
#       Maybe using a dictionary of "recipes" for special cases.


def get_sumvar(ds, vlist):
    """
    Return a derived variable from dataset ds that is the sum of variables in vlist.
    :param ds:
    :param vlist:
    :return:
    """
    checklist = [x in ds.data_vars for x in vlist]
    if all(checklist):
        tmpvar = [ds[v] for v in vlist]
        output = tmpvar[0]
        output.attrs["long_name"] = "derived as: " + tmpvar[0].name
        for i in tmpvar[1:]:
            output += i
            output.attrs["long_name"] += "+" + i.name
        return output
    else:
        raise ValueError("ERROR, variables not present")


def get_diffvar(ds, vlist):
    """
    Return a derived variable from dataset ds that is the difference of variables in vlist.
    :param ds:
    :param vlist:
    :return:
    """
    checklist = [x in ds.data_vars for x in vlist]
    if all(checklist):
        tmpvar = [ds[v] for v in vlist]
        output = tmpvar[0]
        output.attrs["long_name"] = "derived as: " + tmpvar[0].name
        for i in tmpvar[1:]:
            output -= i
            output.attrs["long_name"] += "+" + i.name
        return output
    else:
        raise ValueError("ERROR, variables not present")


def getvar(xrds, varname):
    """
    Return a single variable from a dataset, including special cases.
    :param xrds:
    :param varname:
    :return:
    """
    special_cases = ["PRECT", "CRE", "RESTOM"]
    if varname in xrds.data_vars:
        output = xrds[varname]
    elif varname in special_cases:
        if varname == "PRECT":
            output = get_sumvar(xrds, ["PRECC", "PRECL"])
        if varname == "CRE":
            output = get_sumvar(xrds, ["SWCF", "LWCF"])
        if varname == "RESTOM":
            output = get_diffvar(xrds, ["FSNT", "FLNT"])
        output = output.rename(varname)
    else:
        print(f"Sorry, getvar did not work at variable named {varname}")
        output = None  #
    return output


def getvars(xrds, varlist):
    """
    Return a dataset by searching input dataset for variables in varlist (including special cases).
    :param xrds:
    :param varlist:
    :return:
    """
    special_cases = [v for v in varlist if v not in xrds.data_vars]
    regular_cases = [v for v in varlist if v in xrds.data_vars]
    # TODO: Put these into logging call:
    # print("special:")
    # print(special_cases)
    # print("regular")
    # print(regular_cases)
    if not regular_cases:
        dsout = xr.Dataset()
    else:
        dsout = xrds[regular_cases]  # this is a dataset
    if not special_cases:
        pass
        #  print("No special cases to deal with.")
    else:
        for i in special_cases:
            tmpvar = getvar(xrds, i)
            dsout[i] = tmpvar
    return dsout


def local_open_mfdataset(fils, variable_list=None):
    """
    Open a multifile dataset using xarray, but not with their open_mfdataset function. Instead this takes a list of
    of files and opens each one with open_dataset, and then the variables in the list are put into a new list of
    datasets that are then combined and returned. This is faster than open_mfdataset because it turns off decode_cf,
    which seems to check the coordinates of every file and gets very slow (Limitation of dask? True as of July 2017.).
    -
    FEATURE: This version allows the variable list to include
             PRECT or CRE special cases by using getvars & getvar functions,
             which in turn use the get_sumvar function.
    -
    :param fils: list of files to use (needs to be in order, I think)
    :param variable_list: list of variables to extract into output dataset object
    :return: a single dataset object combined from files and variable list
    """
    dses = [xr.open_dataset(f, decode_cf=False, decode_times=False) for f in fils]
    if variable_list is not None:
        subsetted = [getvars(vs, variable_list) for vs in dses]
        return xr.auto_combine(subsetted)
    else:
        return xr.auto_combine(dses)


def decode_nctime(ds):
    # TODO: Test if this works.
    newtime = cftime.num2date(ds["time"].values, ds["time"].units, ds["time"].calendar)
    ds["time"] = newtime


# ACTIONS SECTION
# Here "actions" are the things that are defined in the "process" input parameter. The function getAction() below is
# just a map between the process array and functions defined herein. These functions perform the "action," and are
# invoked by runner() below; the trick is that since they are invoked abstractly, I think they have to have the same
# arguments.
# TODO: Should the actions know about the data set or not?
def table_stats(ds, fld, out):
    """
    Provide a row of a table for the variable fld. Elements are scalars.
    :param ds: the data set object (used to get cosine weights).
    :param fld: the field that is actually used (could be string and do ds[fld] if that is better).
    :param out: the directory where the table data is written.
    :return: Nothing.
    """
    gw = get_cesm_weight(ds)  # this is just the latitude weights
    gAvg = global_average(fld, gw)
    gMin = fld.min().item()
    gMax = fld.max().item()
    gStd = global_average(fld.std(dim="time"), gw)  # UNWEIGHTED AVG OF TEMPORAL STD DEV
    print(
        " ".join(
            [
                fld.attrs["long_name"],
                str(gAvg.item()),
                str(gMin),
                str(gMax),
                str(gStd.item()),
            ]
        )
    )
    # TODO: Write to a file.


def plot_map(ds, fld, out):
    if "time" in fld.dims:
        Xavg = fld.mean(dim="time")
    else:
        Xavg = fld
    ProjName = "Robinson"
    PlotType = "contourf"
    proj = getattr(ccrs, ProjName)()
    # ADD CYCLIC POINT USING CARTOPY
    lon = Xavg.coords["lon"]
    lon_idx = Xavg.dims.index("lon")
    wrap_data, wrap_lon = add_cyclic_point(Xavg.values, coord=lon, axis=lon_idx)
    fig = plt.figure(figsize=(8, 3))
    ax = fig.add_subplot(111, projection=proj, aspect="auto")
    p = plt.contourf(
        wrap_lon, Xavg.coords["lat"], wrap_data, transform=ccrs.PlateCarree()
    )
    cb = plt.colorbar(p, ax=ax, orientation="vertical")
    cb.set_label(Xavg.name)
    ax.set_global()
    # TODO: Better plot naming mechanism.
    plt.savefig(os.path.join(out, "_".join([Xavg.name, "diag_map.pdf"])))
    plt.clf()  # tell matplotlib we are done with that figure.


def getAction(a):
    """a is a string that is a key to the dictionary here, returns the action to perform"""
    # TODO: Add more actions (polar projection plots, time series plots).
    action_dict = {"tableStats": table_stats, "globalMap": plot_map}
    if a in action_dict:
        # print(f"Found action for {a}, it is {action_dict[a]}")
        return action_dict[a]
    else:
        return None


# CONTROL SECTION
def runner(in_ds, v, a, out):
    for action in a:
        doAct = getAction(action)
        doAct(in_ds, in_ds[v], out)


def run_diags(case, srch, odir, p):
    vlist = list(p.keys())  # list of variables to process
    case_files = sorted(glob.glob(srch))  # the files for the dataset
    # TODO: what happens for variables not in dataset (and not special cases)?
    ds = local_open_mfdataset(case_files, vlist)
    for var, actions in p.items():
        print(f"{var} has {len(actions)} actions to deal with.")
        if len(actions) > 0:
            runner(ds, var, actions, odir)


def checkRequiredInput(fin):
    # TODO: Better checks.
    hasCaseName = "casename" in fin
    hasOutput = "output_directory" in fin
    hasSearch = "search_files" in fin
    hasProcess = "process" in fin
    all_check = (hasCaseName, hasOutput, hasSearch, hasProcess)
    return all(all_check)


if __name__ == "__main__":
    print("Running CAM Diagnostics Script (requires json input file).")
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="CAM Diagnostic Script. Use json file to determine input, "
        "output, and work to be done."
    )
    parser.add_argument(
        "json", type=argparse.FileType("r"), help="path to json file with inputs"
    )
    args = parser.parse_args()
    jin = json.load(args.json)  # "jin" = json input
    # print(json.dumps(jin, indent=4, sort_keys=True))
    if checkRequiredInput(jin):
        run_diags(
            jin["casename"],
            jin["search_files"],
            jin["output_directory"],
            jin["process"],
        )
else:
    print("[INFOMATION] imported cam_diagnostics. Caution advised!")
