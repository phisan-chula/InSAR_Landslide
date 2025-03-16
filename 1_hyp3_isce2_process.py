#
#
#
import os,netrc
import pandas as pd
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse as parse_date

import asf_search as asf
import hyp3_sdk as sdk

def get_credentials(hostname):
    try:
        netrc_path = os.path.expanduser("~/.netrc")  # Get the path to .netrc
        if not os.path.exists(netrc_path):
            return None
        n = netrc.netrc(netrc_path)
        auth = n.authenticators(hostname)
        if auth:
            return auth[0], auth[2]  # auth[0] is username, auth[2] is password
        else:
            return None
    except (FileNotFoundError, OSError, netrc.NetrcParseError) as e:
        print(f"Error reading .netrc: {e}")
        return None

####################################################################
project_name = '2014_mount_edgecumbe'
work_dir = Path.cwd() / project_name
data_dir = work_dir / 'data'

stack_start = parse_date('2014-05-01 00:00:00Z')
stack_end = parse_date('2015-05-01 00:00:00Z')
max_temporal_baseline = 37 #days
data_dir.mkdir(parents=True, exist_ok=True)

####################################################################
search_results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        #polarization=asf.VV,
        intersectsWith='POLYGON((-135.7684 57.0473,-135.7389 57.0473,'\
                  '-135.7389 57.0583,-135.7684 57.0583,-135.7684 57.0473))',
        start=stack_start,
        end=stack_end,
        processingLevel=asf.PRODUCT_TYPE.BURST,
        beamMode=asf.BEAMMODE.IW,
        flightDirection=asf.FLIGHT_DIRECTION.DESCENDING,
    )

baseline_results = asf.baseline_search.stack_from_product(search_results[-1])
columns = list(baseline_results[0].properties.keys()) + ['geometry', ]
data = [list(scene.properties.values()) + [scene.geometry, ] for scene in baseline_results]
stack = pd.DataFrame(data, columns=columns)
stack['startTime'] = stack.startTime.apply(parse_date)
stack = stack.loc[(stack_start <= stack.startTime) & (stack.startTime <= stack_end)]

########################################################################
sbas_pairs = set()
for reference, rt in stack.loc[::-1, ['sceneName', 'temporalBaseline']].itertuples(index=False):
    secondaries = stack.loc[
        (stack.sceneName != reference)
        & (stack.temporalBaseline - rt <= max_temporal_baseline)
        & (stack.temporalBaseline - rt > 0)
    ]
    for secondary in secondaries.sceneName:
        sbas_pairs.add((reference, secondary))
print(f'============================ SBAS paris : {len(sbas_pairs)} ===========================')
for pairs in sbas_pairs:
    print(pairs)

########################################################################
#credentials = get_credentials('phisan-s2.')
#import pdb ; pdb.set_trace()
#hyp3 = sdk.HyP3()
hyp3 = sdk.HyP3(username='phisan',password='Pst1803phi')
jobs = sdk.Batch()
if 1:
    for reference, secondary in sbas_pairs:
        jobs += hyp3.submit_insar_isce_burst_job(
            granule1 = reference,
            granule2 = secondary,
            apply_water_mask = True,
            name = project_name,
            looks = '20x4'
            )

jobs = hyp3.watch(jobs)
now = datetime.now()
start_of_today = datetime(now.year, now.month, now.day)
jobs = hyp3.find_jobs(name=project_name, start=start_of_today)

if 0:
    insar_products = jobs.download_files(data_dir)
    insar_products = [sdk.util.extract_zipped_product(ii) for ii in insar_products]

import pdb ;pdb.set_trace()

