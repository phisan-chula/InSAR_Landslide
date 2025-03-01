#
# 2_Plot_SBAS
#
import re
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import subprocess
import zipfile
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
import tomllib

class SBAS_Management:
    def __init__(self):
        self.ReadCONFIGtoml()
        CACHE = Path('./CACHE')
        CACHE.mkdir(parents=True, exist_ok=True)
        dfs =list()
        for fi in CACHE.rglob('*.txt'):
            self._ASF_INSAR( fi.stem )
            print( f'{self.INSAR}:{fi.stem}...' )
            dfs.append( self.ReadASF_txt( fi ) )
        dfSBAS = pd.concat( dfs,ignore_index=True )
        dfSBAS = dfSBAS[['PROD_ID', 'BL_days', 'Baseline', 'dt_reference', 'dt_secondary']]
        print( dfSBAS )
        ####################################################################
        dfScene = pd.concat( [ dfSBAS.dt_reference, dfSBAS.dt_secondary ] )
        dfScene.sort_values(inplace=True)
        dfScene.drop_duplicates(inplace=True,ignore_index=True)
        dfScene = pd.DataFrame(dfScene,columns=['dt'])
        dfScene.insert(0, 'scene_id', [f'{i:03d}' for i in range(len(dfScene))])
        dfScene['days_0'] = (dfScene['dt'] - dfScene['dt'].iloc[0]).dt.days
        ####################################################################
        def get_scene_id(dt):
            try:
                return dfScene.loc[dfScene['dt'] == dt, 'scene_id'].iloc[0]
            except IndexError:
                return None  # Or handle missing dates as needed
        dfSBAS['id_ref'] = dfSBAS['dt_reference'].apply(lambda x: get_scene_id(x))
        dfSBAS['id_sec'] = dfSBAS['dt_secondary'].apply(lambda x: get_scene_id(x))
        dfSBAS.to_csv( 'CACHE/dfSBAS.csv', sep='\t', index=False)
        self.dfSBAS = dfSBAS
        self.dfScene = dfScene
        self.CalcBaseline()

    def ReadCONFIGtoml(self):
        OPTIONAL = { 'VLINE_DT':None , 'FONT':12 }
        with open("CONFIG.toml", "rb") as f:
            data = tomllib.load(f)
        self.TOML = pd.Series( data )
        for key in OPTIONAL: 
            if key not in self.TOML.keys(): self.TOML[key]=OPTIONAL[key]

    def CalcBaseline(self):
        df = self.dfScene
        df.loc[0,'BL0_meter'] = 0.0
        for grp,grp_row in self.dfSBAS.sort_values( 
                           by='dt_reference' ).groupby('dt_reference'):
            ref_BL0 = df[df.dt==grp].iloc[0].BL0_meter
            for i,row in grp_row.iterrows():
                sec_BL0 = df[df.dt==row.dt_secondary].iloc[0].BL0_meter
                if np.isnan(sec_BL0):
                    idx = df.loc[df.dt==row.dt_secondary].iloc[0] 
                    df.loc[ idx.name, 'BL0_meter'] = ref_BL0 + row.Baseline
                else:
                    #print(f'Value {sec_BL0}  exist' ) 
                    df.loc[ idx.name, 'BL0_meter'] = row.Baseline

    def PlotNetworkX(self):
        nodes = list(self.dfScene.scene_id)
        edges = self.dfSBAS[['id_ref','id_sec']].values.tolist()
        G = nx.Graph() 
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        # Access graph properties (example):
        print( "Isolates : ", list(nx.isolates(G)) )
        print("Number of nodes:", G.number_of_nodes())
        print("Number of edges:", G.number_of_edges())
        print("Nodes:", G.nodes())
        print("Edges:", G.edges())
        #components = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        #for idx,G in enumerate(components,start=1):
        #    print(f"Component {idx}: Nodes: {G.nodes()} Edges: {G.edges()}")
        #import pdb; pdb.set_trace()
        # Get connected components
        components = list(nx.connected_components(G))

        # Assign separate layouts for each component
        pos = {}
        for i, comp in enumerate(components):
            subgraph = G.subgraph(comp)
            sub_pos = nx.spring_layout(subgraph, seed=42)
            # Offset each component in a grid layout
            offset = np.array([i * 3, 0])  # Spread along x-axis
            for node in sub_pos:
                pos[node] = sub_pos[node] + offset
        # Plot the graph
        plt.figure(figsize=(8, 6))
        nx.draw(G, pos, with_labels=True, node_color="lightblue", 
                   edge_color="gray", node_size=800, font_size=12)
        plt.title("Graph with Non-Overlapping Components")
        plt.show()

    def _ASF_INSAR(self, s):
        P1 = r'^S1_\d{6}_IW\d_\d{8}_\d{8}_.*$'  # "S1_654321_IW9_20231201_20231231_other"
        P2 = r"S1[A-Z]{2}_\d{8}T\d{6}_\d{8}T\d{6}_.*"
        if bool(re.match(P1, s)):   self.INSAR = 'ISCE2_S1BURST',3
        elif bool(re.match(P2, s)): self.INSAR = 'GAMMA_S1FULL',5   
        else:
            print( f'Unknown file pattern "{s}"...' ); raise 

    def DELTA_days(self,dt1,dt2):
        return round((dt1-dt2).total_seconds()/(3600*24))

    def ReadASF_txt(self, filepath ):
        #import pdb ; pdb.set_trace()
        with open(filepath, 'r') as file:
                lines = file.readlines()
                # Remove trailing newlines from each line
                lines = [line.rstrip('\n') for line in lines]
        data = {}
        data['PROD_ID'] = filepath.stem.split('_')[-1]
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass #keep string
                data[key] = value
        FMT = '%Y%m%dT%H%M%S'   # date + time
        PROC,POS = self.INSAR 
        data['dt_reference'] = pd.to_datetime(data['Reference Granule'].\
                                        split('_')[POS],format=FMT )
        data['dt_secondary'] = pd.to_datetime(data['Secondary Granule'].\
                                        split('_')[POS],format=FMT )
        ##import pdb; pdb.set_trace()
        data['BL_days'] =  self.DELTA_days( data['dt_secondary'],data['dt_reference'] ) 
        return pd.DataFrame([data]) # Create a DataFrame from the dictionary

    def PlotShortBaseline(self):
        FS = self.TOML.FONT # font size
        days = self.DELTA_days( self.dfSBAS.dt_reference.max(), 
                                self.dfSBAS.dt_reference.min() )
        DESC = self.dfSBAS.Baseline.describe()
        #import pdb; pdb.set_trace()
        fig,ax1 = plt.subplots(figsize=(10, 6))
        ax2 = ax1.twiny()
        for i,row in self.dfSBAS.iterrows():
            xs = [ row['dt_reference'], row['dt_secondary'] ]
            ys = [ row['Baseline'],     row['Baseline']  ]
            xs_=xs[0]+(xs[1]-xs[0])/2 ; ys_ = ys[0]
            ax1.plot( xs,ys) 
            ax1.scatter(xs,ys,s=50,ec='black', marker='o',fc='none',alpha=0.7)
            ax1.text( xs_,ys_, row.PROD_ID, c='red', size=FS, ha='center' )
            ax1.text( xs[0],ys[0], row.id_ref, size=FS,ha='right',va='top' )
            ax1.text( xs[1],ys[1], row.id_sec, size=FS,ha='left',va='top' )
            ax1.text( xs_,ys_, f'{row.BL_days}d', c='blue', size=FS, ha='center', va='top' )
        for dt in self.TOML.VLINE_DT:
            ax1.axvline( x=pd.to_datetime(dt) )
        ax1.set_xlabel('Date and Time')
        ax1.set_ylabel('BL_meter')
        ax2.set_xlim( 0, days )
        ax2.set_xlabel('Temporal Baseline (days)')
        # Format the y-axis to display dates and times correctly
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator()) #Auto-locate the dates.
        CNT,MIN,MAX = int(DESC['count']), int(DESC['min']), int(DESC['max'])
        ax1.set_title(f'SBAS Interfergram scenes:{CNT},BL_min:{MIN}m., BL_max:{MAX}m.')
        ax1.grid(True)
        plt.tight_layout() # Improves plot layout
        plt.show()

#################################################################
#################################################################
#################################################################
if __name__=="__main__":
    sbas = SBAS_Management()
    sbas.PlotNetworkX()
    sbas.PlotShortBaseline()
