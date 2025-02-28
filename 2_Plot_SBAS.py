#
#
#
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

def create_networkx(df, reference_col='dt_reference', second_col='dt_second'):
    if reference_col not in df.columns or second_col not in df.columns:
        print("Error: One or both datetime columns not found.")
        return None
    G = nx.DiGraph()  # Use DiGraph for directed edges (reference -> second)
    for index, row in df.iterrows():
        reference_time = row[reference_col]
        second_time = row[second_col]
        G.add_edge(reference_time, second_time)
    return G

def DELTA_days(dt1,dt2):
    return round((dt1-dt2).total_seconds()/(3600*24))

def ReadASF_txt( filepath ):
    with open(filepath, 'r') as file:
            lines = file.readlines()
            # Remove trailing newlines from each line
            lines = [line.rstrip('\n') for line in lines]
    data = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            try:
                # Attempt to convert to float or int
                value = float(value)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                pass #keep string
            data[key] = value
    stem = filepath.stem.split('_')
    data['dt_reference'] =  pd.to_datetime( stem[1], format='%Y%m%dT%H%M%S')
    data['dt_second'] =  pd.to_datetime( stem[2], format='%Y%m%dT%H%M%S')
    data['BL_days'] =  DELTA_days( data['dt_second'],data['dt_reference'] ) 
    data['_days'] = stem[3]
    data['PROD_ID'] = stem[-1]
    #import pdb; pdb.set_trace()
    df = pd.DataFrame([data]) # Create a DataFrame from the dictionary
    return df

def PlotSB( df ):
    days = DELTA_days( df.dt_reference.max(), df.dt_reference.min() )
    DESC = df.Baseline.describe()
    fig,ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twiny()
    for i,row in df.iterrows():
        xs = [ row['dt_reference'], row['dt_second'] ]
        ys = [ row['Baseline'],     row['Baseline']  ]
        ax1.plot( xs,ys) 
        ax1.scatter(xs, ys, s=30, ec='black', marker='o',
                fc='none', cmap='viridis', alpha=0.7)
        xs_=xs[0]+(xs[1]-xs[0])/2 ; ys_ = ys[0]
        ax1.text( xs_,ys_, row.PROD_ID, fontsize=8,ha='center' )
        #import pdb; pdb.set_trace()
    ax1.axvline( x=pd.to_datetime( '2024-08-17 23:11:10') )
    ax1.axvline( x=pd.to_datetime( '2024-08-29 23:11:10') )
    ax1.set_xlabel('Date and Time')
    ax1.set_ylabel('BL_meter')
    ax2.set_xlim( 0, days )
    ax2.set_xlabel('Temporal Baseline (days)')
    # Format the y-axis to display dates and times correctly
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator()) #Auto-locate the dates.
    CNT,MIN,MAX = int(DESC['count']), int(DESC['min']), int(DESC['max'])
    ax1.set_title(f'SBAS Interfergram for Phuket, scene:{CNT}, Bl_min:{MIN}m, Bl_max:{MAX}m')
    ax1.grid(True)
    plt.tight_layout() # Improves plot layout
    plt.show()

def PlotNetworkX( G ):
    # Visualize the graph (optional)
    pos = nx.spring_layout(G)  # Layout algorithm
    nx.draw(G, pos, with_labels=True, node_size=400, 
            node_color='skyblue', font_size=8, arrowsize=20)
    plt.show()
#################################################################
#################################################################
#################################################################
CACHE = Path('./CACHE')
CACHE.mkdir(parents=True, exist_ok=True)

dfs =list()
for fi in CACHE.rglob('*.txt'):
    #print( fi )
    dfs.append( ReadASF_txt( fi ) )

dfSBAS = pd.concat( dfs,ignore_index=True )
dfSBAS = dfSBAS[['PROD_ID', 'BL_days', '_days' , 'Baseline',  'dt_reference', 'dt_second']]
print( dfSBAS )
####################################################################
dfScene = pd.concat( [ dfSBAS.dt_reference, dfSBAS.dt_second ] )
dfScene.sort_values(inplace=True)
dfScene.drop_duplicates(inplace=True,ignore_index=True)
dfScene = pd.DataFrame(dfScene,columns=['dt'])
dfScene.insert(0, 'scene_id', [f'{i:03d}' for i in range(len(dfScene))])
#dfScene['BL0_meter'] = np.nan
def get_scene_id(dt, df_scene):
    try:
        return dfScene.loc[dfScene['dt'] == dt, 'scene_id'].iloc[0]
    except IndexError:
        return None  # Or handle missing dates as needed
dfSBAS['id_ref'] = dfSBAS['dt_reference'].apply(lambda x: get_scene_id(x, dfScene))
dfSBAS['id_sec'] = dfSBAS['dt_second'].apply(lambda x: get_scene_id(x, dfScene))
dfSBAS.to_csv( 'CACHE/dfSBAS.csv', sep='\t', index=False)
import pdb; pdb.set_trace()
####################################################################
G = create_networkx(dfSBAS, reference_col='id_ref', second_col='id_sec')
# Access graph properties (example):
print( "Isolates : ", list(nx.isolates(G)) )
print("Number of nodes:", G.number_of_nodes())
print("Number of edges:", G.number_of_edges())
#print("Nodes:", G.nodes())
#print("Edges:", G.edges())
PlotNetworkX( G )

#####################################################################
dfScene.loc[0,'BL0_meter'] = 0.0
for grp,grp_row in dfSBAS.sort_values( by='dt_reference' ).groupby('dt_reference'):
    ref_BL0 = dfScene[ dfScene.dt==grp].iloc[0].BL0_meter
    for i,row in grp_row.iterrows():
        sec_BL0 = dfScene[ dfScene.dt==row.dt_second].iloc[0].BL0_meter
        if np.isnan(sec_BL0):
            idx = dfScene.loc[dfScene.dt==row.dt_second].iloc[0] 
            dfScene.loc[ idx.name, 'BL0_meter'] = ref_BL0 + row.Baseline
        else:
            #print(f'Value {sec_BL0}  exist' ) 
            dfScene.loc[ idx.name, 'BL0_meter'] = row.Baseline
import pdb; pdb.set_trace()
PlotSB( dfSBAS )
