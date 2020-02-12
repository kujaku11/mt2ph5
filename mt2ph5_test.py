# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 01:29:26 2020

@author: jpeacock
"""
import os
import glob
import datetime
from ph5.core import experiment
import mttoph5

# =============================================================================
# Test
# =============================================================================
#ts_fn = r"c:\Users\jpeacock\Documents\GitHub\sandbox\ts_test.EX"
ph5_fn = r"c:\Users\jpeacock\Documents\test_ph5.ph5"
#nfn = r"c:\Users\jpeacock\OneDrive - DOI\MountainPass\FieldWork\LP_Data\Mnp300a\DATA.BIN"
fn_list = glob.glob(r"c:\Users\jpeacock\Documents\imush\O015\*.Z3D")


st = datetime.datetime.now()

if os.path.exists(ph5_fn):
    try:
        os.remove(ph5_fn)
    except PermissionError:
        ph5_obj = experiment.ExperimentGroup(nickname='test_ph5',
                                     currentpath=os.path.dirname(ph5_fn))
        ph5_obj.ph5open(True)
        ph5_obj.ph5close()

### initialize a PH5 object
ph5_obj = experiment.ExperimentGroup(nickname='test_ph5',
                                     currentpath=os.path.dirname(ph5_fn))
ph5_obj.ph5open(True)
ph5_obj.initgroup()

### initialize mt2ph5 object
mt_obj = mttoph5.MTtoPH5()
mt_obj.ph5_obj = ph5_obj

# we give it a our trace and should get a message
# back saying done as well as an index table to be loaded
message = mt_obj.to_ph5(fn_list[0:10])

# be nice and close the file
ph5_obj.ph5close()

et = datetime.datetime.now()

diff = et - st
print('='*56)
print('--> To PH5 took {0} seconds'.format(diff.total_seconds()))