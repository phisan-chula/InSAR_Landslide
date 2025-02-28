#
#
#
from pathlib import Path
import pandas as pd
import geopandas as gpd
import subprocess

import zipfile
import os

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
PATH_INT='./InterferogramZip'

CACHE = Path('./CACHE')
CACHE.mkdir(parents=True, exist_ok=True)

for fi in Path( PATH_INT).glob('*.zip'):
    print( fi )
    TXT = f'{fi.stem}/{fi.stem}.txt'
    VERT_TIF = f'{fi.stem}/{fi.stem}_vert_disp.tif'
    VERT_XML = f'{fi.stem}/{fi.stem}_vert_disp.tif.xml'
    extract_from_zip(fi,  TXT     ,  CACHE )
    extract_from_zip(fi,  VERT_TIF,  CACHE )
    extract_from_zip(fi,  VERT_XML,  CACHE )
    #import pdb; pdb.set_trace()
