# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 17:05:20 2019

@author: jpeacock
"""

# =============================================================================
# Imports
# =============================================================================
import logging
import os
import re
import glob
from pathlib import Path
import numpy as np

from ph5.core import experiment
from ph5.core import columns

# =============================================================================
# Begin tools
# =============================================================================

### Initialize a PH5 file
def initialize_ph5_file(ph5_fn):
    """Initialize a PH5 file given a file name.  This will build the 
    appropriate groups needed in a PH5 file.
    
    :param ph5_fn: full path to ph5 file to be created
    :type ph5_fn: string or Path
    
    :return: opened message
    :rtype: bool [True | False]
    
    :return: an open ph5 object
    :rtype: PH5.Expermiment
    """
    
    ph5_path = Path(ph5_fn)
    
    ph5_obj = experiment.ExperimentGroup(nickname=ph5_path.name,
                                         currentpath=ph5_path.parent)
    ph5_obj.ph5open(True)
    ph5_obj.initgroup()
    
    print("Made PH5 File {0}".format(ph5_path))
    
    return ph5_obj

### add survey metadata
def add_survey_metadata(ph5_obj, survey_dict):
    """
    add survey metdata to experiment table
    
    survey_dict
    
    ===================================== =============================== ======
    Key                                   Description                     Type
    ===================================== =============================== ======
    experiment_id_s                       experiment id                   string
    net_code_s                            net code                        string
    nickname_s                            experiment nickname             string
    longname_s                            experiment long name            string
    PIs_s                                 list of principle investigators string
    institutions_s                        list of institutions involved   string
    north_west_corner/coordinate_system_s coordinate system               string
    north_west_corner/projection_s        projection type (ex. Albers)    string
    north_west_corner/ellipsoid_s         ellipsoid used (ex. WGS84)      string
    north_west_corner/X/value_d           north west corner value in      float
                                          northing direction             
    north_west_corner/X/units_s           units of X value                string
    north_west_corner/Y/value_d           north west corner value in      float
                                          easting direction             
    north_west_corner/Y/units_s           units of Y value                string
    north_west_corner/Z/value_d           north west corner value in      float
                                          vertical direction             
    north_west_corner/Z/units_s           units of Z value                string
    south_east_corner/coordinate_system_s coordinate system               string
    south_east_corner/projection_s        projection type (ex. Albers)    string
    south_east_corner/ellipsoid_s         ellipsoid used (ex. WGS84)      string
    south_east_corner/X/value_d           south east corner value in      float
                                          northing direction             
    south_east_corner/X/units_s           units of X value                string
    south_east_corner/Y/value_d           south east corner value in      float
                                          easting direction             
    south_east_corner/Y/units_s           units of Y value                string
    south_east_corner/Z/value_d           south east corner value in      float
                                          vertical direction             
    south_east_corner/Z/units_s           units of Z value                string
    summary_paragraph_s                   summary of survey (1024 char.)  string
    ===================================== =============================== ======
    """
    survey_table = ph5_obj.ph5_g_experiment.Experiment_t
    
    columns.append(survey_table, survey_dict)    
            
    print("updated Experiment_t")
    
def add_column_to_experiment_t(ph5_obj, new_col_name, new_col_values, 
                               new_col_type, type_len=32):
    """
    Add a column to experiment table
    
    """
    
    ph5_table = ph5_obj.ph5_g_experiment.Experiment_t
    
    new_table = columns.add_column(ph5_table,
                                   new_col_name,
                                   new_col_values,
                                   new_col_type,
                                   type_len)
    
    return new_table
            
 
### Add a station 
def add_station(ph5_obj, station, station_dict):
    """
    add a station to existing ph5 file
    
        * will add an entry to receivers_t
        * will add entry to Sorts_t
    
    :param ph5_obj: an open ph5_object
    :param station: station name
    :type station: string
    
    :param station_dict: dictionary containing important metadata
    :type station_dict: dictionary
    
    :returns:
    """
    
    pass
    

    
# =============================================================================
# Tests    
# =============================================================================

ph5_test_obj = initialize_ph5_file(r"c:\Users\jpeacock\Documents\GitHub\PH5\ph5\test_data\test.ph5")

add_survey_metadata(ph5_test_obj, 
                    {'experiment_id_s':'01234', 
                     'MT station':'alpha',
                     'north_west_corner/X/value_d':40.0})

add_column_to_experiment_t(ph5_test_obj, 
                           'declination_d',
                           [10.5], 
                           'float')
