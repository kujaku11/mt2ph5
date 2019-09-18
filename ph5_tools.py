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
import datetime

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

def load_json(json_fn):
    """
    read in a json file 
    
    :param json_fn: full path to json file to read
    :type json_fn: string
    
    :returns: dictionary of metadata
    """
    with open(json_fn, 'r') as fid:
        return_dict = json.load(fid)
        
    return return_dict

# =============================================================================
#  A generic class with tools to convert any data into PH5
# =============================================================================
class generic2ph5(object):
    """
    Generic class with tools to convert time-series data into PH5.  This class
    is meant to be as general as possible that can be used up the chain by 
    more specific data formats.
    
    There are quite a few subtilties that one needs to keep track of.  As far 
    as I understand it the way to convert your data would be as follows
    
        1.  
    
    """
    
    def __init__(self):
        
        self.ph5_obj = None
        
    @property
    def ph5_path(self):
        return self.ph5_obj.currentpath
        
    ### Initialize a PH5 file
    def open_ph5_file(self, ph5_fn):
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
        
        self.ph5_obj
    
    def get_arrays(self):
        """
        get array table information
        """    
        arrays = []
        for name in self.ph5_obj.ph5_g_sorts.names():
            array_list, null = self.ph5_obj.ph5_g_sorts.read_arrays(name)
            for entry in array_list:
                arrays.append(entry)
                
        return arrays
    
    def get_das_station_map(self):
        """
        Checks if array tables exist
        returns None
        otherwise returns a list of dictionaries
        containing das serial numbers and stations
        :return: list
        """
        array_names = self.ph5_obj.ph5_g_sorts.namesArray_t()
        if not array_names:
            return []
        station_list = []
        # use tables where to search array tables and find matches
        for array_name in array_names:
            table = self.ph5_obj.ph5.get_node('/Experiment_g/Sorts_g/{0}'.format(
                array_name))
            data = table.read()
            for row in data:
                station_list.append({'serial': row[4][0], 
                                     'station': row[13],
                                     'array_name': array_name})
        
        das_station_map = []
        for station in station_list:
            if station not in das_station_map:
                das_station_map.append(station)
        table = None
    
        return das_station_map
    
    def get_sort_array_name(self, station):
        """
        get the sort array name for a given station
        """
        
        das_station_map = get_das_station_map(self.ph5_obj)
        for entry in das_station_map:
            ### the entry is binary, need to decode into unicode
            if station in entry['station'].decode():
                return entry['array_name']
        return None
        
    def open_mini(self, mini_num):
        """
        Open PH5 file, miniPH5_xxxxx.ph5
        :type: str
        :param mini_num: name of mini file to open
        :return class: ph5.core.experiment, str: name
        """
    
        mini_num = '{0:05}'.format(mini_num)
        filename = "miniPH5_{0}.ph5".format(mini_num)
        mini_ph5_obj = experiment.ExperimentGroup(nickname=filename,
                                                  currentpath=self.ph5_path)
        mini_ph5_obj.ph5open(True)
        mini_ph5_obj.initgroup()
        
        return mini_ph5_obj, filename
     
    def get_current_mini_num(self, station, first_mini=1,
                             mini_size_max = 26843545600):
        """
        get the current mini number
        """    
        mini_list = get_mini_list(self.ph5_path)
        if not mini_list:
            current_mini = first_mini
        else:
            current_mini = None
            mini_map = get_mini_map(mini_list)
            das_station_map = get_das_station_map(self.ph5_obj) 
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
                    if (mini[2] < mini_size_max):
                        current_mini = largest
                    else:
                        current_mini = largest + 1
        return current_mini
    
    def get_mini_size(self, mini_fn):
        """
        :param mini_num: str
        :return: size of mini file in bytes
        """
        return os.path.getsize(mini_fn)
    
    def get_mini_list(self):
        """
        takes a directory and returns a list of all mini files
        in the current directory
    
        :type str
        :param dir
        :return: list of mini files
        """
        miniPH5RE = re.compile(r".*miniPH5_(\d+)\.ph5")
        mini_list = []
        for entry in os.listdir(self.ph5_path):
            # Create full path
            mini_path = os.path.join(self.ph5_path, entry)
            if miniPH5RE.match(entry):
                mini_list.append(mini_path)
        return mini_list
    
    def get_mini_map(self, mini_list):
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
            mini_size = get_mini_size(exrec.filename)
            das_list = []
            for g in all_das:
                name = g.split('_')[-1]
                das_list.append(name)
            mini_map.append((mini_num, das_list, mini_size))
            exrec.ph5close()
            
        return mini_map   
    
    ### add survey metadata
    def add_survey_metadata(self, survey_dict):
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
        
        keys_not_added = columns.append(self.ph5_obj.ph5_g_experiment.Experiment_t,
                                        survey_dict)
    
        for key, value in keys_not_added.items():
            try:
                col_len = min([len(value), 32])
            except TypeError:
                col_len = 32
      
            try:
                columns.add_column(self.ph5_obj.ph5_g_experiment.Experiment_t,
                                   key,
                                   [value],
                                   get_column_type(key),
                                   type_len=col_len)
            except AssertionError as error:
                print('Could not add {0} because {1}'.format(key, error))
    
        
    def add_column_to_experiment_t(self, new_col_name, new_col_values, 
                                   new_col_type, type_len=32):
        """
        Add a column to experiment table
        
        """
        
        ph5_table = self.ph5_obj.ph5_g_experiment.Experiment_t
        
        new_table = columns.add_column(ph5_table,
                                       new_col_name,
                                       new_col_values,
                                       new_col_type,
                                       type_len)
        
        return new_table
                
     
    ### Add a station 
    def add_array_to_sorts(self, array_name, array_dict):
        """
        add array metadata to main ph5 file
            * will add entry to Sorts_t
        
        An array as defined in PH5 is a single channel for a station at a given
        sampling rate.  Therefore you need an array entry for every channel 
        collected for every station in the survey.  If the channel is collected
        at different sampling rates, you need an entry for each.
        
        This is also the best place to add any metadata that isn't hard coded in
        -- apparently --
        
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
        if not array_name in self.ph5_obj.ph5_g_sorts.namesArray_t():
            self.ph5_obj.ph5_g_sorts.newArraySort(array_name)
        self.ph5_obj.ph5_g_sorts.populateArray_t(array_dict, name=array_name)
        
        return array_name
    
    def add_reciever_to_table(self, receiver_dict):
        """
        Add a receiver to the receivers table
        """
        ### add receiver information to table
        self.ph5_obj.ph5_g_receivers.populateReceiver_t(receiver_dict)
        n_row = self.ph5_obj.ph5_g_receivers.ph5_t_receiver.nrows
        
        return n_row
    
    def add_response_to_table(self, response_dict):
        """
        Add a response to the receivers table
        
        .. note:: not complete yet
        """
        ### add receiver information to table
        self.ph5_obj.ph5_g_responses.populateResponse_t(response_dict)
        n_row = self.ph5_obj.ph5_g_responses.ph5_t_response.nrows
        
        return n_row
    
    def add_station_mini(self, station_name):
        """
        Make a station mini_ph5_xxxxx file
        
        :param station_name: station name
        :type station_name: string
        
        :returns: das_group_name, mini_ph5_object
        """
        ### get mini number first
        mini_num = self.get_current_mini_num(self.ph5_obj, station_name)
        mini_ph5_obj, filename = self.open_mini(mini_num, self.ph5_path)
        
        ### make sure there is a station group
        das_group = mini_ph5_obj.ph5_g_receivers.getdas_g(station_name)
        if not das_group:
            das_group, dt, rt, tt = mini_ph5_obj.ph5_g_receivers.newdas(station_name)
        mini_ph5_obj.ph5_g_receivers.setcurrent(das_group)
        
        return das_group_name, mini_ph5_obj
    
    def add_channel(self, mini_ph5_obj, station, channel_dict, channel_array,
                    channel_meta_dict, data_type='int32', description=None):
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
        #Make sure we aren't overwriting a data array
        count = 1
        while True:
            next_num = '{0:05}'.format(count)
            data_array_name = "Data_a_{0}".format(next_num)
            node = mini_ph5_obj.ph5_g_receivers.find_trace_ref(data_array_name)
            if not node:
                break
            count = count + 1
            continue
        
        ### add the appropriate array name to the metadata
        channel_dict['array_name_data_a'] = data_array_name
        
        ### create new data array
        mini_ph5_obj.ph5_g_receivers.newarray(channel_dict['array_name_data_a'],
                                              channel_array,
                                              dtype=data_type,
                                              description=description)
        
        ### add response table entry number to metadata
        channel_dict['response_table_n_i'] = self.get_response_n(station,
                    channel_dict['sample_rate_i'],
                    channel_dict['channel_number_i'])
        ### add receiver table entry number to metadata
        channel_dict['receiver_table_n_i'] = self.get_receiver_n(station,
                    channel_dict['sample_rate_i'],
                    channel_dict['channel_number_i'])
        ### add the channel metadata to the das table
        mini_ph5_obj.ph5_g_receivers.populateDas_t(channel_dict)
        
        ### add channel metadata to appropriate sorts array
        sorts_array_name = self.get_sort_array_name(station)
        self.add_array_to_sorts(sorts_array_name, channel_meta_dict)
        
        ### make time index entry
        t_index_entry = self.make_time_index_entry(channel_meta_dict,
                                                   mini_ph5_obj.nickname)
        self.ph5_obj.ph5_g_receivers.populateIndex_t(t_index_entry)
        
        ### update external references
        self.update_external_reference(t_index_entry)
        
        return t_index_entry
    
    def make_time_index_entry(self, meta_dict, mini_name):
        """
        make a time index entry
        """
        t_list = ['ascii_s', 'epoch_l', 'micro_seconds_i', 'type_s']
        
        entry_dict = {}
        entry_dict['serial_number_s'] = meta_dict['id_s']
        for t_key in t_list:
            entry_dict['start_time/{0}'.format(t_key)] = meta_dict['deploy_time/{0}'.format(t_key)]
            entry_dict['end_time/{0}'.format(t_key)] = meta_dict['pickup_time/{0}'.format(t_key)]
    
        ### make time stamp
        now = datetime.datetime.now()
        entry_dict['time_stamp/ascii_s'] = now.isoformat()
        entry_dict['time_stamp/epoch_l'] = int(now.timestamp())
        entry_dict['time_stamp/micro_seconds_i'] = now.microsecond
        entry_dict['time_stamp/type_s'] = 'BOTH'
        
        ### add external references
        entry_dict['hdf5_path_s'] = "/Experiment_g/Receivers_g/Das_g_{0}".format(entry_dict['serial_number_s'])
        entry_dict['external_file_name_s'] = "./{0}".format(mini_name)
        
        return entry_dict
    
    def update_external_reference(self, time_entry_dict):
        """
        make external reference for mini file
        """
        
        external_fn = time_entry_dict['external_file_name_s'][2:]
        external_dir = time_entry_dict['hdf5_path_s']
        
        target = '{0}:{1}'.format(external_fn, external_dir)
        external_group = external_dir.split('/')[3]
        
        try:
            group_node = self.ph5_obj.ph5.get_node(external_dir)
            group_node.remove()
    
        except Exception:
            pass
        
        #   Re-create node
        try:
            self.ph5_obj.ph5.create_external_link('/Experiment_g/Receivers_g', 
                                                  external_group, target)
        except Exception as error:
            print('x'*10)
            print(error)
            print('x'*10)
        
    def get_receiver_n(self, station, sample_rate, channel_number):
        """
        get receiver table index for given station, given channel
        """
        # figure out receiver and response n_i
        for array_entry in get_arrays(self.ph5_obj):
            if (array_entry['sample_rate_i'] == sample_rate and
                array_entry['channel_number_i'] == channel_number and
                array_entry['id_s'] == station):
                return array_entry['receiver_table_n_i']
    
    def get_response_n(self, station, sample_rate, channel_number):
        """
        get receiver table index for given station, given channel
        """
        # figure out receiver and response n_i
        for array_entry in get_arrays(self.ph5_obj):
            if (array_entry['sample_rate_i'] == sample_rate and
                array_entry['channel_number_i'] == channel_number and
                array_entry['id_s'] == station):
                return array_entry['response_table_n_i']



    
# =============================================================================
# Tests    
# =============================================================================
ph5_fn = r"c:\Users\jpeacock\Documents\GitHub\PH5_py3\ph5\test_data\test.ph5"
survey_json = r"c:\Users\jpeacock\Documents\GitHub\mt2ph5\survey_metadata.json"
station_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\station_metadata.json"
receiver_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\receiver_metadata.json"
channel_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\channel_metadata.json"

if os.path.exists(ph5_fn):
    os.remove(ph5_fn)

ph5_test_obj = open_ph5_file(ph5_fn)

### add Survey metadata to file
survey_dict = load_json(survey_json)
add_survey_metadata(ph5_test_obj, 
                    survey_dict)

#### add station
das_group_name, mini_ph5_obj = add_station_mini(ph5_test_obj, 'mt01')

#### add channel data
### 1 -- add receiver to table
receiver_dict = load_json(receiver_json)
n_receiver = add_reciever_to_table(ph5_test_obj, receiver_dict)

### 2 -- add array to sorts
array_dict = load_json(station_json)
array_dict['receiver_table_n_i'] = n_receiver
new_array = add_array_to_sorts(ph5_test_obj, 
                               ph5_test_obj.ph5_g_sorts.nextName(),
                               array_dict)

### 3 -- add array data
channel_dict = load_json(channel_json)
t_entry = add_channel(ph5_test_obj, mini_ph5_obj, 'mt01', channel_dict, 
                      np.random.randint(2**12, size=2**16, dtype=np.int32),
                      array_dict)

### TODO: need to add time index table and external references



### Add a column to metadata table 
#add_column_to_experiment_t(ph5_test_obj, 
#                           'declination_d',
#                           [10.5], 
#                           'float')
