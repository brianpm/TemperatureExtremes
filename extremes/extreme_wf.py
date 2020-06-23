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
    fil1 = Path(inputs['quantiles_directory']) / inputs['quantiles_file']
    if not fil1.is_file():
        if 'quantiles_parallel' in inputs:
            qp = inputs['quantiles_parallel']
        else:
            qp = False
        quant_ds = Save_Quantile_Dataset._run(ds, x, parallel=qp)
        utils.save_ds(quant_ds, fil1)
        logger.info(f"Finished [1] File saved: {inputs['quantiles_file']}")
    else:
        logger.info(f"File Exists: {inputs['quantiles_file']}\n LOAD FILE.")
        quant_ds = xr.open_dataset(fil1)
        

    # 2.
    fil2 = Path(inputs['event_detection_dir']) / inputs['event_detection_fil']
    if not fil2.is_file():
        event_ds = prototype_event_detection._run(ds, quant_ds, inputs['input_var_name'])
        utils.save_ds(event_ds, fil2)
        logger.info(f"Finished [2] File saved: {inputs['event_detection_fil']}")
    else:
        logger.info("Event detection file found. Loading.")
        event_ds = xr.open_dataset(fil2)

    # 3.
    fil3 = Path(inputs['event_attribute_dir'])/inputs['event_attribute_fil']
    attributes_ds = event_attributes.run(event_ds)
    utils.save_ds(attributes_ds, fil3)
    logger.info(f"Finished [3] File saved: {inputs['event_attribute_fil']}")




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
