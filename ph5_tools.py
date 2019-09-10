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
import dateutil

from ph5.core import experiment
from ph5.core import columns

# =============================================================================
# Begin tools
# =============================================================================
def read_date_time(time_string):
    """
    read a time string and convert it to the proper formats
    
    :param str time_string: time string date-time
    
    :returns: iso-format, epoch, microseconds
    """
    
    dt_obj = dateutil.parser.parse(time_string)
    
    return dt_obj.isoformat(), int(dt_obj.timestamp()), dt_obj.microsecond


### Initialize a PH5 file
def open_ph5_file(ph5_fn):
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
def add_array_to_sorts(ph5_obj, array_name, array_dict):
    """
    add station metadata to main ph5 file
    
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
    ### make a new sorts array table from given name
    if not array_name in ph5_obj.ph5_g_sorts.namesArray_t():
        ph5_obj.ph5_g_sorts.newArraySort(array_name)
    ph5_obj.ph5_g_sorts.populateArray_t(array_dict, name=array_name)
    
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

def add_station_group(ph5_obj, station_name):
    """
    add station to receivers_g
    
    1. Make new mini_ph5 file for the station
    2. Load DAS metadata into das table
    3. Add channel data as new array, add to array table
    4. Update index table
    5. Update external references
    
    :param station_name: station name
    :type station_name: string
    
    :returns:das_group, das_table, self.ph5_t_receiver, self.ph5_t_time
    """
    
    new_das_group = ph5_obj.ph5_g_receivers.newdas(station_name)
    das_group_name = new_das_group[0]
    
    mini_num = get_current_mini_num(ph5_obj, station_name)
    mini_ph5_obj, filename = open_mini(mini_num, ph5_obj.currentpath)
    
    return das_group_name, mini_ph5_obj
    
def add_channel(das_g_name, channel_dict, channel_array):
    """
    add channel to station
    
    channel dict
    
    ============================ =============================== ==============
    Key                          Description                     Type 
    ============================ =============================== ==============
    time/ascii_s                 start time of the channel       string
    time/epoch_l                 start time of channel           int
    time/micro_seconds           start time micro seconds        int
    time/type_s                  [ both | string | epoch]        string 
    sample_rate_i                sample rate                     int
    sample_rate_multiplier_i     sample rate multiplier          int
    channel_number_i             channel number                  int
    raw_file_name_s              name of file data came from     string 
    sample_count_i               number of samples in array      int
    receiver_table_n_i           number of receiver info         int
    response_table_n_i           number of response info         int
    array_name_data_a            name of data array              string
    ============================ =============================== ==============

    .. note:: should find receiver, response number automatically, user should 
              not have to input those.
              
    """
    
    
    pass

def get_das_station_map(ph5_obj):
    """
    Checks if array tables exist
    returns None
    otherwise returns a list of dictionaries
    containing das serial numbers and stations
    :return: list
    """
    array_names = ph5_obj.ph5_g_sorts.namesArray_t()
    if not array_names:
        return None
    station_list = []
    # use tables where to search array tables and find matches
    for _array in array_names:
        tbl = ph5_obj.ph5.get_node('/Experiment_g/Sorts_g/{0}'.format(
            _array))
        data = tbl.read()
        for row in data:
            station_list.append({'serial': row[4][0], 'station': row[13]})
    das_station_map = []
    for station in station_list:
        if station not in das_station_map:
            das_station_map.append(station)
    tbl = None

    return das_station_map
 
def get_current_mini_num(ph5_obj, station, first_mini=1,
                         mini_size_max = 26843545600):
    """
    get the current mini number
    """    
    mini_list = get_mini_list(ph5_obj.currentpath)
    if not mini_list:
        current_mini = first_mini
    else:
        current_mini = None
        mini_map = get_mini_map(mini_list)
        das_station_map = get_das_station_map(ph5_obj) 
        for mini in mini_map:
            for entry in das_station_map:
                if (entry['serial'] in mini[1] and
                        entry['station'] == station):
                    current_mini = mini[0]
            if not current_mini:
                largest = 0
                for station in mini_map:
                    if station[0] >= largest:
                        largest = station[0]
                if (get_size_mini(largest) < mini_size_max):
                    current_mini = largest
                else:
                    current_mini = largest + 1
    return current_mini

def get_size_mini(mini_num):
    """
    :param mini_num: str
    :return: size of mini file in bytes
    """
    mini_num = str(mini_num).zfill(5)
    mini_path = "miniPH5_{0}.ph5".format(mini_num)
    return os.path.getsize(mini_path)

def get_mini_list(ph5_path):
    """
    takes a directory and returns a list of all mini files
    in the current directory

    :type str
    :param dir
    :return: list of mini files
    """
    miniPH5RE = re.compile(r".*miniPH5_(\d+)\.ph5")
    mini_list = []
    for entry in os.listdir(ph5_path):
        # Create full path
        mini_path = os.path.join(ph5_path, entry)
        if miniPH5RE.match(entry):
            mini_list.append(mini_path)
    return mini_list

def get_mini_map(mini_list):
    """
    :type list
    :param existing_minis: A list of mini_files with path
    :return:  list of tuples containing
    what mini file contains what serial #s
    """
    mini_map = []
    for mini_fn in mini_list:
        mini_num = int(mini_fn.split('.')[-2].split('_')[-1])
        exrec = experiment.ExperimentGroup(nickname=mini_fn)
        exrec.ph5open(True)
        exrec.initgroup()
        all_das = exrec.ph5_g_receivers.alldas_g()
        das_list = []
        for g in all_das:
            name = g.split('_')[-1]
            das_list.append(name)
        mini_map.append((mini_num, das_list))
        exrec.ph5close()
    return mini_map   

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

ph5_test_obj = open_ph5_file(ph5_fn)

### add Survey metadata to file
survey_dict = load_json(survey_json)
add_survey_metadata(ph5_test_obj, 
                    survey_dict)

### add station
array_dict = load_json(station_json)
new_array = add_array_to_sorts(ph5_test_obj, 
                               ph5_test_obj.ph5_g_sorts.nextName(),
                               array_dict)

### add receiver
receiver_dict = load_json(receiver_json)
n_receiver = add_reciever_to_table(ph5_test_obj, receiver_dict)

### Add a column to metadata table 
#add_column_to_experiment_t(ph5_test_obj, 
#                           'declination_d',
#                           [10.5], 
#                           'float')
