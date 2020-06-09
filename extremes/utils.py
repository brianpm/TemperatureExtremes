# UTILS
import xarray as xr

def save_ds(ds, pth):
    """Save DataSet as compressed netCDF4"""
    # encode = {'zlib': True, 'complevel': 5, "_FillValue": None}
    encode = {'zlib': True, 'complevel': 5,}
    if isinstance(ds, xr.Dataset):
        enc_dv = {xname: encode for xname in ds.data_vars}
    else:
        enc_dv = {ds.name: encode}
    enc_c = {xname: {"_FillValue": None} for xname in ds.coords}
    enc = {**enc_c, **enc_dv}
    ds.to_netcdf(pth, format="NETCDF4", encoding=enc)

