# UTILS

def save_ds(ds, pth):
    """Save DataSet as compressed netCDF4"""
    encode = {'zlib': True, 'complevel': 5, "_FillValue": None}
    enc_dv = {xname: encode for xname in ds.data_vars}
    enc_c = {xname: {"_FillValue": None} for xname in ds.coords}
    enc = {**enc_c, **enc_dv}
    ds.to_netcdf(pth, format="NETCDF4", encoding=enc)

