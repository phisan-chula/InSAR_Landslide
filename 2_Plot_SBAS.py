#
# 2_Plot_SBAS
#
import os,re
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import subprocess
import zipfile
import itertools
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
import tomllib
from SBAS_mgmt import *

class SBAS_Network( SBAS_Management ) :
    def __init__(self,ARGS):
        self.ARGS = ARGS
        super().__init__(ARGS.TOML) 
        dfs =list()
        #import pdb; pdb.set_trace()
        TXT_PATH = self.TOML.RESULT / 'INTERFEROGRAM'  # unzip *.txt; *.tif
        for fi in TXT_PATH.rglob('*.txt'):
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
        dfSBAS.to_csv( self.TOML.RESULT / 'dfSBAS.csv', sep='\t', index=False)
        self.dfSBAS = dfSBAS
        self.dfScene = dfScene
        self.CalcBaseline()

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
        print( f'Composing graph ....')
        nodes = list(self.dfScene.scene_id)
        edges = self.dfSBAS[['id_ref','id_sec']].values.tolist()
        G = nx.Graph() 
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        #######################################################################
        # Assign separate layouts for each component
        components = list(nx.connected_components(G))
        pos = {}
        for i, comp in enumerate(components):
            subgraph = G.subgraph(comp)
            sub_pos = nx.spring_layout(subgraph, seed=42)
            # Offset each component in a grid layout
            offset = np.array([i * 3, 0])  # Spread along x-axis
            for node in sub_pos:
                pos[node] = sub_pos[node] + offset
        # Plot the graph
        #import pdb; pdb.set_trace()
        if self.ARGS.networkx:
            plt.figure(figsize=(8, 6))
            nx.draw(G, pos, with_labels=True, node_color="lightblue", 
                   alpha=0.5, edge_color="gray", node_size=800, font_size=12)
            plt.title("Graph with Non-Overlapping Components")
            plt.show()
        #######################################################################
        components = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        self.dfScene['nCompo'] = 0
        self.dfSBAS['nCompo'] = 0
        for idx,G in enumerate(components,start=0):
            if self.ARGS.dump:
                print(f"Component {idx}: Nodes: {G.nodes()} Edges: {G.edges()}")
            else:
                print(f"Component {idx}: Nodes: {G.number_of_nodes()} Edges: {G.number_of_edges()}")
            for node in G.nodes:
                if node in self.dfScene['scene_id'].values:
                    self.dfScene.loc[self.dfScene['scene_id'] == node, 'nCompo'] = idx
            for edge in G.edges:
                mask1 = (self.dfSBAS['id_ref'] == edge[0]) & (self.dfSBAS['id_sec']==edge[1]) 
                mask2 = (self.dfSBAS['id_ref'] == edge[1]) & (self.dfSBAS['id_sec']==edge[0]) 
                self.dfSBAS.loc[mask1|mask2,'nCompo'] = idx

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
        PROCESSOR,POS = self.INSAR 
        data['dt_reference'] = pd.to_datetime(data['Reference Granule'].\
                                        split('_')[POS],format=FMT )
        data['dt_secondary'] = pd.to_datetime(data['Secondary Granule'].\
                                        split('_')[POS],format=FMT )
        data['BL_days'] =  self.DELTA_days( data['dt_secondary'],data['dt_reference'] ) 
        return pd.DataFrame([data]) # Create a DataFrame from the dictionary

    def PlotShortBaseline(self):
        cmap = plt.get_cmap('tab10', 10)
        colors = cmap(np.linspace(0, 1, 10))
        CYC = itertools.cycle( colors )
        #CYC = itertools.cycle( ['red', 'green', 'blue', 'yellow'] )
        FS = self.TOML.FONT # font size
        DAYS = self.DELTA_days( self.dfSBAS.dt_reference.max(), 
                                self.dfSBAS.dt_reference.min() )
        DESC = self.dfSBAS.Baseline.describe()
        #import pdb; pdb.set_trace()
        NCOMPO = len(self.dfScene.nCompo.value_counts())
        fig,ax1 = plt.subplots(figsize=(10, 6))
        ax2 = ax1.twiny()
        for grp,row_grp in self.dfSBAS.groupby( 'nCompo' ):
            if NCOMPO>1: c = next(CYC)
            for i,row in row_grp.iterrows(): 
                xs = [ row['dt_reference'], row['dt_secondary'] ]
                xs_= xs[0]+(xs[1]-xs[0])/2 
                if NCOMPO==1: 
                    c = next(CYC)
                    BL0_ref = self.dfScene[ self.dfScene.scene_id==row.id_ref].iloc[0].BL0_meter
                    BL0_sec = self.dfScene[ self.dfScene.scene_id==row.id_sec].iloc[0].BL0_meter
                    ys = [ BL0_ref,  BL0_sec]
                else:
                    ys = [ row['Baseline'],     row['Baseline']  ]
                ys_= ys[0]+(ys[1]-ys[0])/2 
                ax1.plot(xs,ys,color=c) 
                ax1.text( xs_,ys_, row.PROD_ID, c=c, size=FS, ha='center' )
                ax1.text( xs_,ys_, f'{row.BL_days}d', c=c, size=FS, ha='center', va='top' )
                if NCOMPO>1:
                    ax1.scatter(xs,ys,s=100,ec=c, marker='o',fc='none',alpha=0.7)
                    ax1.text( xs[0],ys[0], row.id_ref, c=c, size=FS,ha='right',va='top' )
                    ax1.text( xs[1],ys[1], row.id_sec, c=c, size=FS,ha='left',va='top' )
        if NCOMPO==1:
            for i,row in self.dfScene.iterrows():
                ax1.text( row['dt'], row.BL0_meter , row.scene_id, c='black', size=FS,ha='center',va='center' )
                ax1.scatter( row['dt'], row.BL0_meter, s=400,ec='black', marker='o',fc='none',alpha=0.7)
        for dt in self.TOML.VLINE_DT:
            ax1.axvline( x=pd.to_datetime(dt), color='black', linestyle=':' )
        self.PlotNewPairs(ax1)
        ax1.set_xlabel('Date and Time')
        ax1.set_ylabel('BL_meter')
        ax2.set_xlim( 0, DAYS )
        ax2.set_xlabel('Temporal Baseline (days)')
        # Format the y-axis to display dates and times correctly
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator()) #Auto-locate the dates.
        CNT,MIN,MAX = int(DESC['count']), int(DESC['min']), int(DESC['max'])
        ax1.set_title(f'SBAS Interfergram compo:{NCOMPO} granules:{CNT} BL_min:{MIN}m. BL_max:{MAX}m.')
        ax1.grid(True)
        plt.tight_layout() # Improves plot layout
        plt.show()

    def PlotNewPairs(self,AX):
        for pair in self.TOML.NEW_PAIRS:
            fr = self.dfScene.loc[ self.dfScene[ 'scene_id']== pair[0], ['dt','BL0_meter'] ].iloc[0]
            to = self.dfScene.loc[ self.dfScene[ 'scene_id']== pair[1], ['dt','BL0_meter'] ].iloc[0]
            AX.plot( [fr['dt'],to['dt']],[fr.BL0_meter,to.BL0_meter ],
                        lw=5, color='black', linestyle='--',alpha=0.7) 
            import pdb; pdb.set_trace()
        print(pair)

#################################################################
#################################################################
#################################################################
import argparse
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('TOML', help="TOML config file")
    parser.add_argument("-x","--networkx", action="store_true", 
            help="plot networkX graph(s)")
    parser.add_argument("-d","--dump", action="store_true", 
            help="dump nodes and edges for each component(s)")
    ARGS = parser.parse_args()
    #import pdb; pdb.set_trace()
    sbas = SBAS_Network(ARGS)
    sbas.PlotNetworkX()
    sbas.PlotShortBaseline()
