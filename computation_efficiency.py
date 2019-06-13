import xarray as xr
import numpy as np
from numba import jit

ds = xr.open_dataset("/Users/brianpm/Downloads/CERES_EBAF-TOA_Ed4.0_Subset_200003-201810.nc")

da = ds['toa_cre_net_mon']

# print(da)

# calculation of IQR

# 1. Xarray 
# q25 = da.quantile(0.25, dim='time', interpolation='linear')
# real	0m3.243s
# user	0m2.552s
# sys	0m0.337s


# 2. Numpy
# q25 = np.percentile(da, 25, axis=0, overwrite_input=False, interpolation='linear', keepdims=False)
# real	0m1.827s
# user	0m0.951s
# sys	0m0.411s
# Note... this is much faster, but we didn't rebuild a dataarray object.

# 2.b Numpy with nanpercentile
# q25 = np.nanpercentile(da, 25, axis=0, interpolation='linear')

# real	0m4.129s
# user	0m3.147s
# sys	0m0.419s

# 3. Reshape and loop

# 3.a : Just doing a loop is very slow
tmp = da.stack(z=('lat','lon'))
# c = 0
# for j, zz in enumerate(tmp.z):
# 	c += 1 
# print(c)

# 3.b : A loop that is compiled:
@jit(nopython=True)
def space_loop(arr):
	c = 0
	for j in np.arange(arr.shape[1]):
		c += 1
	return c
# cnt = space_loop(tmp.values)
# print(cnt)
# this is actually pretty fast without jit:
# real	0m1.352s
# user	0m1.063s
# sys	0m0.316s

# with jit, it slows down b/c we are including compilation time
# real	0m2.726s
# user	0m1.285s
# sys	0m0.493s

# 3.c now loop and do the calculation using numpy function:
@jit(nopython=False)
def space_loop_qant(arr):
	result = []
	for j in np.arange(arr.shape[1]):
		good_vals = np.isfinite(arr[:,j])
		result.append(np.percentile(arr[good_vals,j], 25, interpolation='linear'))
	return np.array(result)

tmptmp = tmp.values
q25 = space_loop_qant(tmptmp)
print(q25)
# without jit:
# real	0m3.234s
# user	0m2.963s
# sys	0m0.307s

