#
# 0_SBAS
#
import os,re
from pathlib import Path
import numpy as np
import pandas as pd
import zipfile
import tomllib

class SBAS_Management:
    def __init__(self,TOML):
        self.ReadCONFIGtoml(TOML)
        self.TOML.RESULT.mkdir(parents=True, exist_ok=True)

    def ReadCONFIGtoml(self,TOML):
        #import pdb; pdb.set_trace()
        OPTIONAL = { 'RESULT': './RESULT' ,'NEW_PAIR': None, 
                     'VLINE_DT':None , 'FONT':12 }
        with open(TOML, "rb") as f:
            data = tomllib.load(f)
        self.TOML = pd.Series( data )
        for key in OPTIONAL: 
            if key not in self.TOML.keys(): self.TOML[key]=OPTIONAL[key]
        self.TOML.INT_ZIP = Path( self.TOML.INT_ZIP )
        self.TOML.RESULT  = Path( self.TOML.RESULT )

    def _ASF_INSAR(self, s):
        # ISCE Burst product  "S1_654321_IW9_20231201_20231231_*"
        P1 = r'^S1_\d{6}_IW\d_\d{8}_\d{8}_.*$'  
        # GAMMA product "S1AA_20241016T231111_20241028T231111_*"
        P2 = r"S1[A-Z]{2}_\d{8}T\d{6}_\d{8}T\d{6}_.*"
        if bool(re.match(P1, s)):   self.INSAR = 'ISCE2_S1BURST',3
        elif bool(re.match(P2, s)): self.INSAR = 'GAMMA_S1FULL',5   
        else:
            print( f'Unknown file pattern "{s}"...' ); raise 

    def DELTA_days(self,dt1,dt2):
        return round((dt1-dt2).total_seconds()/(3600*24))

###################################################################
if __name__ == "__main__":
    SBAS_Management('CONFIG_PK_S.toml')
