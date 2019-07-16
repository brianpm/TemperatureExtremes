# extreme_wf

import yaml
import argparse
from pathlib import Path

def _run_main(inputs):

    # For each of 1, 2, & 3, the return from .run()
    # should be a DataSet that is the same as what 
    # is saved when running the script individually.
    # This saves us from re-loading data.
    # 1.
    quant_ds = Save_Quantile_Dataset.run()
    # 2.
    event_ds = prototype_event_detection.run()
    # 3.
    attributes_ds = event_attributes.run()
    # Save the DataSets:
    utils.save_ds(quant_ds, inputs['quantiles_file'])
    utils.save_ds(event_ds, inputs['event_detection_fil'])
    utils.save_ds(attributes_ds, inputs['event_attribute_fil'])



if __name__ == "__main__":
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
    _run_main(inputs)