# notes

# YAML file

We might want to provide only the file name for output and then add a creation date and the `.nc` suffix programmatically.

We might also need to make a hierarchy for the original input data. That would allow easier selection for single-file or multi-file input.

# Event Attributes
In the first version, I saved the "initial index" which was the actual time index from the raw data (or detection) that corresponds to the first day of the events. This is not robust because it requires being able to go back and re-load the same data to get the right day. This would break, for example, if we wanted to use a different data set to get meteorological conditions during the event; doing that would require going back to the data to extract the date. A better solution is to include the date in the attribute file. 

Tested in python with xarray (cftime). I can just make an array of datetime objects and xarray knows to convert them to numbers with an appropriate units string upon saving to netCDF. Reading works great, returning the array of datetime objects if decoding is turned on.