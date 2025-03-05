#
#
#
from pathlib import Path
import pandas as pd
import geopandas as gpd
import subprocess

import zipfile
import os
import importlib
from SBAS_mgmt import *

def extract_from_zip(zip_filepath, file_to_extract=None, output_dir="."):
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            os.makedirs(output_dir, exist_ok=True)
            if file_to_extract:
                if file_to_extract in zip_ref.namelist():
                    zip_ref.extract(file_to_extract, output_dir)
                    print(f"Extracted: {file_to_extract} to {os.path.join(output_dir, file_to_extract)}")
                else:
                    print(f"File '{file_to_extract}' not found in zip archive.")
            else:
                for file_info in zip_ref.infolist():
                    zip_ref.extract(file_info, output_dir)
                    print(f"Extracted: {file_info.filename} to {os.path.join(output_dir, file_info.filename)}")
    except FileNotFoundError:
        print(f"Error: Zip file not found at {zip_filepath}")
    except zipfile.BadZipFile:
        print(f"Error: {zip_filepath} is not a valid zip file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


#################################################################
###################################################################
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('TOML', help="TOML config file")
    parser.add_argument("-d","--dump", action="store_true",
            help="dump nodes and edges for each component(s)")
    ARGS = parser.parse_args()    
    #import pdb ;pdb.set_trace()
    sbas = SBAS_Management( ARGS.TOML )
    files_for_mintpy = ['.txt',
                            '_water_mask.tif',
                            '_corr.tif',
                            '_conncomp.tif',
                            '_unw_phase.tif',
                            '_dem.tif',
                            '_lv_theta.tif',
                            '_lv_phi.tif']
    PATH_UNZIP = sbas.TOML.RESULT / 'INTERFEROGRAM'
    PATH_UNZIP.mkdir(parents=True,exist_ok=True)
    import pdb; pdb.set_trace()
    for fzip in sbas.TOML.INT_ZIP.glob('*.zip'):
        print( fzip )
        for fi_minpy in files_for_mintpy:
            full = f'{fzip.stem}/{fzip.stem}{fi_minpy}'
            print( f'extracting ...{full}') 
            extract_from_zip(fzip, full, PATH_UNZIP )
