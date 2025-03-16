from pathlib import Path
from typing import List, Union
from osgeo import gdal
from pathlib import Path
from typing import List, Union
import subprocess
from SBAS_mgmt import *

gdal.UseExceptions()
MINTPY_CONFIG = """
mintpy.load.processor        = hyp3
##---------interferogram datasets:
mintpy.load.unwFile          = {data_dir}/*/*_unw_phase_clipped.tif
mintpy.load.corFile          = {data_dir}/*/*_corr_clipped.tif
mintpy.load.connCompFile     = {data_dir}/*/*_conncomp_clipped.tif
##---------geometry datasets:
mintpy.load.demFile          = {data_dir}/*/*_dem_clipped.tif
mintpy.load.incAngleFile     = {data_dir}/*/*_lv_theta_clipped.tif
mintpy.load.azAngleFile      = {data_dir}/*/*_lv_phi_clipped.tif
mintpy.load.waterMaskFile    = {data_dir}/*/*_water_mask_clipped.tif
mintpy.troposphericDelay.method = no
##---------misc:
mintpy.plot = no
mintpy.network.coherenceBased = no
"""

def get_common_overlap(file_list: List[Union[str, Path]]) -> List[float]:
    """Get the common overlap of  a list of GeoTIFF files
    Arg:
        file_list: a list of GeoTIFF files
    Returns:
         [ulx, uly, lrx, lry], the upper-left x, upper-left y, lower-right x, and lower-right y
         corner coordinates of the common overlap
    """

    corners = [gdal.Info(str(dem), format='json')['cornerCoordinates'] for dem in file_list]

    ulx = max(corner['upperLeft'][0] for corner in corners)
    uly = min(corner['upperLeft'][1] for corner in corners)
    lrx = min(corner['lowerRight'][0] for corner in corners)
    lry = max(corner['lowerRight'][1] for corner in corners)
    return [ulx, uly, lrx, lry]

def clip_hyp3_products_to_common_overlap(data_dir: Union[str, Path], 
                                    work_dir: Union[str, Path], 
                                    overlap: List[float]) -> None:
    files_for_mintpy = [ '_water_mask.tif',
                        '_corr.tif',
                        '_conncomp.tif',
                        '_unw_phase.tif',
                        '_dem.tif',
                        '_lv_theta.tif',
                        '_lv_phi.tif']

    for extension in files_for_mintpy:
        for file in data_dir.rglob(f'*{extension}'):
            dst_file = work_dir / f'{file.stem}_clipped{file.suffix}'
            print( f'{str(dst_file)} srcDS=str(file), projWin=overlap')
            #gdal.Translate(destName=str(dst_file), srcDS=str(file), projWin=overlap)
            cmd = ['gdal_translate','-projWin', 
                    ' '.join(map(str, overlap)), 
                     str(file),
                     str(dst_file) ]
            cmd = ' '.join(cmd)
            print( cmd )
            result = subprocess.run(cmd, shell=True,
                          capture_output=True) #execute the command
            #import pdb ;pdb.set_trace()
            print( result )
            print(f"gdal_translate completed successfully.")

###############################################################################
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('TOML', help="TOML config file")
    parser.add_argument("-c","--clip", action="store_true",
            help="clip dataset as DEM for MintPy processging")
    parser.add_argument("-p","--process", action="store_true",
            help="do process MintPy ")
    ARGS = parser.parse_args()
    sbas = SBAS_Management( ARGS.TOML )

    work_dir =  sbas.TOML.RESULT / 'WORKING'
    work_dir.mkdir( parents=True, exist_ok=True) 
    data_dir =  sbas.TOML.RESULT / 'INTERFEROGRAM' 

    files = data_dir.glob('*/*_dem.tif')
    overlap = get_common_overlap(files)
    print( f'DEM coverage : {overlap}...' )
    if ARGS.clip:
        clip_hyp3_products_to_common_overlap(data_dir, work_dir, overlap)

    if ARGS.process:
        mintpy_config = work_dir / 'mintpy_config.txt'
        mintpy_config.write_text( MINTPY_CONFIG.format(data_dir=data_dir ) )
        CMD_MINTPY = f'smallbaselineApp.py --dir {work_dir} {mintpy_config}'
        print(CMD_MINTPY)
        #import pdb ;pdb.set_trace()
        process = subprocess.run( CMD_MINTPY,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True,  # Raise CalledProcessError for non-zero return codes
                )
        import pdb ; pdb.set_trace()
