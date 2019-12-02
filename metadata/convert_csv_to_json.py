# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 11:57:15 2019

@author: jpeacock
"""

import pandas as pd
import json
import os



csv_fn_base = r"c:\Users\jpeacock\Downloads\MT Metadata Standards - {0}.csv"
save_path = r"c:\Users\jpeacock\Documents\GitHub\mt2ph5"

for name in ['Survey', 'Station', 'Run', 'Data Logger', 'Electrics', 'Magnetics']:
    csv_fn = csv_fn_base.format(name) 
    json_fn = os.path.join(save_path, 
                           '{0}_metadata_mt.json'.format(name.lower()))
    
    df = pd.read_csv(csv_fn, usecols=['Parameter', 'Explanation'], skiprows=1)
    
    json_dict = {}
    for key, value in zip(df.Parameter, df.Explanation):
        json_dict[key] = value
    
    with open(json_fn, 'w') as fid: 
        json.dump(json_dict, fid, indent=4)