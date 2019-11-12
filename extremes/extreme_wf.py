#!/usr/bin/env python

# extreme_wf
import logging
import yaml
import argparse
from pathlib import Path
import xarray as xr

# import our local modules
import utils


def _load_data(loc, srch):
    return xr.open_mfdataset(f"{loc}/{srch}", combine='by_coords')


def _run_main(inputs):
    import Save_Quantile_Dataset
    logger.info("1")
    import prototype_event_detection
    logger.info("2")
    import event_attributes
    logger.info("3")

    # For each of 1, 2, & 3, the return from .run()
    # should be a DataSet that is the same as what 
    # is saved when running the script individually.
    # This saves us from re-loading data.
    ds = _load_data(inputs['input_directory'], inputs['input_file_glob'])
    x = ds[inputs['input_var_name']]

    # 1.
    quant_ds = Save_Quantile_Dataset._run(ds, x)
    utils.save_ds(quant_ds, inputs['quantiles_file'])

    # 2.
    event_ds = prototype_event_detection._run(ds, quant_ds, inputs['input_var_name'])
    utils.save_ds(event_ds, inputs['event_detection_fil'])

    # 3.
    attributes_ds = event_attributes.run(event_ds)
    utils.save_ds(attributes_ds, inputs['event_attribute_fil'])



if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # collect argument file
    parser = argparse.ArgumentParser(description='Use YAML file for configuration.')
    parser.add_argument('ifil', type=str, help='path to YAML file with inputs')
    args = parser.parse_args()
    # data can be "loaded" easily by using a YAML file that is just a dictionary:
    input_file = Path(args.ifil)

    # read the YAML
    with open(input_file, 'r') as f:
        # use safe_load instead load
        iyaml = yaml.safe_load(f)
    # "validate" the YAML input
    assert("input_directory" in iyaml)
    # start the run:
    _run_main(iyaml)