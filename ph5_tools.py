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
import json
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

def get_column_type(keyword):
    """
    get the column type from the key word
    """
    if keyword[-1] in ['s']:
        col_type = 'string'
    elif keyword[-1] in ['l', 'i']:
        col_type = 'int'
    elif keyword[-1] in ['d']:
        col_type = 'float'
        
    else:
        raise ValueError('Cannot determine type of {0} keyword')
    return col_type

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
    
    keys_not_added = columns.append(ph5_obj.ph5_g_experiment.Experiment_t,
                                    survey_dict)

    for key, value in keys_not_added.items():
        try:
            col_len = min([len(value), 32])
        except TypeError:
            col_len = 32
  
        try:
            columns.add_column(ph5_obj.ph5_g_experiment.Experiment_t,
                               key,
                               [value],
                               get_column_type(key),
                               type_len=col_len)
        except AssertionError as error:
            print('Could not add {0} because {1}'.format(key, error))
            
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
def add_station_to_sorts(ph5_obj, station, station_dict):
    """
    add a station to existing ph5 file
    
        * will add an entry to receivers_t
        * will add entry to Sorts_t
    
    :param ph5_obj: an open ph5_object
    :param station: station name
    :type station: string
    
    :param station_dict: dictionary containing important metadata
    :type station_dict: dictionary
    
    :returns: new array name
    
    station_dict should have
    
    ============================ =============================== ==============
    Key                          Description                     Type 
    ============================ =============================== ==============
    id_s                         station id number               string
    location/X/value_d           northing value                  float 
    location/X/units_s           northing units                  string
    location/Y/value_d           easting value                   float
    location/Y/units_s           easting units                   string
    location/Z/value_d           elevation value                 float 
    location/Z/units_s           elevation units                 string
    location/coordinate_system_s location coordinate system      string  
                                 (ex. WGS84) 
    location/projection_s        coordinate projection           string
    location/ellipsoid_s         coordinate ellipsoid            string 
    location/description_s       description of station site     string
    deploy_time/ascii_s          time of deployment isoformat    string 
    deploy_time/epoch_l          time of deployment epoch sec    int
    deploy_time/micro_seconds_i  time of deployment micro sec    int  
    deploy_time/type_s           Both, String, Epoch             string
    pickup_time/ascii_s          pick up time isoformat          string
    pickup_time/epoch_l          pick up time epoch sec          int
    pickup_time/micro_seconds_i  pick up time micro sec          int
    pickup_time/type_s           Both, String, Epoch             string
    das/serial_number_s          data logger serial number       string
    das/model_s                  data logger model               string
    das/manufacturer_s           data logger manufacturer        string
    das/notes_s                  data logger notes               string  
    sensor/serial_number_s       sensor serial number            string
    sensor/model_s               sensor model                    string
    sensor/manufacturer_s        sensor manufacturer             string
    sensor/notes_s               sensor notes                    string  
    description_s                description of station          string
    seed_band_code_s             seed something                  string
    sample_rate_i                sample rate (samples/second)    string                      
    sample_rate_multiplier_i     sample rate multiplier          string
    seed_instrument_code_s       seed something                  string
    seed_orientation_code_s      seed something                  string 
    seed_location_code_s         seed something                  string
    seed_station_name_s          seed something                  string
    channel_number_i             channel number                  int 
    receiver_table_n_i           receiver table number           int
    response_table_n_i           response table number           int
    ============================ =============================== ==============
    """
    ### make new array in sorts table
    ### get next available array name first 
    array_name = ph5_obj.ph5_g_sorts.nextName()
   
    ### make a new sorts array table from given name 
    ph5_obj.ph5_g_sorts.newArraySort(array_name)
    array_ref = columns.TABLES['/Experiment_g/Sorts_g/{0}'.format(array_name)]
    columns.populate(array_ref, station_dict)
    
    return array_name

def add_reciever_to_table(ph5_obj, receiver_dict):
    """
    Add a receiver to the receivers table
    """
    ### add 
    ph5_obj.ph5_g_receivers.populateReceiver_t(receiver_dict)
    n_row = ph5_obj.ph5_g_receivers.ph5_t_receiver.nrows
    
    return n_row
    
def open_mini(mini_num, ph5_path):
    """
    Open PH5 file, miniPH5_xxxxx.ph5
    :type: str
    :param mini_num: name of mini file to open
    :return class: ph5.core.experiment, str: name
    """

    mini_num = '{0:05}'.format(mini_num)
    filename = "miniPH5_{0}.ph5".format(mini_num)
    mini_ph5_obj = experiment.ExperimentGroup(nickname=filename,
                                       currentpath=ph5_path)
    mini_ph5_obj.ph5open(True)
    mini_ph5_obj.initgroup()
    
    return mini_ph5_obj, filename

def add_station(ph5_obj, station_name):
    """
    add station to receivers_g/das_g_station_name
    
    """
    
    return ph5_obj.ph5_g_receivers.newdas(station_name)

def add_channel(ph5_obj, channel_dict, channel_array):
    """
    add channel to station
    """
    pass

def load_json(json_fn):
    """
    read in ajson file 
    
    :param json_fn: full path to json file to read
    :type json_fn: string
    
    :returns: dictionary of metadata
    """
    with open(json_fn, 'r') as fid:
        return_dict = json.load(fid)
        
    return return_dict
    
# =============================================================================
# Tests    
# =============================================================================
ph5_fn = r"c:\Users\jpeacock\Documents\GitHub\PH5_py3\ph5\test_data\test.ph5"
survey_json = r"c:\Users\jpeacock\Documents\GitHub\mt2ph5\survey_metadata.json"
station_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\station_metadata.json"
receiver_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\receiver_metadata.json"

if os.path.exists(ph5_fn):
    os.remove(ph5_fn)

ph5_test_obj = initialize_ph5_file(ph5_fn)

### add Survey metadata to file
survey_dict = load_json(survey_json)
add_survey_metadata(ph5_test_obj, 
                    survey_dict)

### add station
station_dict = load_json(station_json)
new_array = add_station_to_sorts(ph5_test_obj, 
                                 'MT01',
                                 station_dict)

### add receiver
receiver_dict = load_json(receiver_json)
n_receiver = add_reciever_to_table(ph5_test_obj, receiver_dict)

### Add a column to metadata table 
#add_column_to_experiment_t(ph5_test_obj, 
#                           'declination_d',
#                           [10.5], 
#                           'float')
