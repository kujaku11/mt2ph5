# -*- coding: utf-8 -*-
"""
==============
PH5 Tools
==============

These are generic tools for building a PH5 file.  They are pretty basic to 
hopefully make it easier to adapt different data types.

.. note:: All times entered are validated to be UTC and be consistent between
          ascii and epoch times.  If there is a difference ascii format is
          assumed to be the correct one.

TODO: 
    - validate PH5 file made from tests.
    - try more difficult tests.


Created on Wed Jul 17 17:05:20 2019

@author: jpeacock
"""

# =============================================================================
# Imports
# =============================================================================
import os
import re
import json
from pathlib import Path
import numpy as np
import dateutil
import datetime

from ph5.core import experiment
from ph5.core import columns

# =============================================================================
# global variables
# =============================================================================
t_list = ['ascii_s', 'epoch_l', 'micro_seconds_i', 'type_s']

# =============================================================================
# Begin tools
# =============================================================================
def read_date_time(time_string):
    """
    read a time string and convert it to the proper formats
    
    :param str time_string: time string date-time
    
    :return: iso-format, epoch, microseconds
    """
    
    dt_obj = check_timezone(dateutil.parser.parse(time_string))
    
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
    
    :return: dictionary of metadata
    """
    with open(json_fn, 'r') as fid:
        return_dict = json.load(fid)
        
    return return_dict

def check_timezone(dt_object):
    """
    make sure the dt_object is aware of being UTC
    """
    
    if dt_object.tzinfo is None or dt_object.tzinfo != datetime.timezone.utc:
        return dt_object.replace(tzinfo=datetime.timezone.utc)
    
    return dt_object        
    

def validate_time_metadata(meta_dict):
    """
    validate the time in a given data dictionary to be sure that the ascii
    is the same as the epoch
    """
    t_keys = {'deploy_time':{}, 'pickup_time':{}, 'start_time':{},
              'end_time':{}, 'time_stamp':{}}
    for key, value in meta_dict.items():
        if 'declination' in key:
            continue
        base = key.split('/')[0]
        if 'ascii_s' in key:
            t_keys[base]['ascii_s'] = check_timezone(dateutil.parser.parse(value))     
        elif 'epoch' in key:
            try:
                value += meta_dict['{0}/{1}'.format(base, 'micro_seconds_i')]
            except KeyError:
                pass
            t_keys[base]['epoch_l'] = check_timezone(datetime.datetime.fromtimestamp(float(value)))
            
    for t_key, t_value in t_keys.items():
        dt_obj_s = None
        dt_obj_e = None
        try:
            dt_obj_s = t_value['ascii_s']
        except KeyError:
            pass
        try:
            dt_obj_e = t_value['epoch_l']
        except KeyError:
            pass

        if dt_obj_e and dt_obj_s:
            if dt_obj_e != dt_obj_s:
                print('ascii time and epoch time are different.')
                print('ascii time is {0}'.format(dt_obj_s.isoformat()))
                print('epoch time is {0}'.format(dt_obj_e.isoformat()))
                print('Difference is {0}'.format(dt_obj_s - dt_obj_e))
                print('Using ascii time as the correct one')
                iso, ts, ms = read_date_time(dt_obj_s.isoformat())
                t_dict = {'ascii_s':iso, 'epoch_l':ts, 'micro_seconds_i':ms}
                for s_key, s_value in t_dict.items():
                    meta_dict['{0}/{1}'.format(t_key, s_key)] = s_value
        elif not dt_obj_e and not dt_obj_s:
            continue
                
        elif not dt_obj_e:
            iso, ts, ms = read_date_time(dt_obj_s.isoformat())
            t_dict = {'ascii_s':iso, 'epoch_l':ts, 'micro_seconds_i':ms}
            for s_key, s_value in t_dict.items():
                    meta_dict['{0}/{1}'.format(t_key, s_key)] = s_value
                
        elif not dt_obj_s:
            iso, ts, ms = read_date_time(dt_obj_e.isoformat())
            t_dict = {'ascii_s':iso, 'epoch_l':ts, 'micro_seconds_i':ms}
            for s_key, s_value in t_dict.items():
                    meta_dict['{0}/{1}'.format(t_key, s_key)] = s_value
    
    return meta_dict
        
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
    
        1. Get your metadata into dictionaries following the formats below
        2. Make a ph5 file
        3. Add receiver metadata 
        ..note:: there should be one entry per channel per station, if the 
                 channels changed for some reason this should be a separate
                 entry.
        4. Loop over each station and add in channel data and metadata.
        
    
    """
    
    def __init__(self):
        
        self.ph5_obj = None
        self.mini_size_max = 26843545600
        
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
        
        :Example:
            
        >>> ph5_obj = generic2ph5()
        >>> ph5_obj.open_ph5_file("/home/test/test.ph5")
    
        """
        
        ph5_path = Path(ph5_fn)
        
        self.ph5_obj = experiment.ExperimentGroup(nickname=ph5_path.name,
                                             currentpath=ph5_path.parent)
        self.ph5_obj.ph5open(True)
        self.ph5_obj.initgroup()
        
        print("Made PH5 File {0}".format(ph5_path))
    
    def get_arrays(self):
        """
        read in each array entry as a dictionary from sorts group and append
        to a list.
        
        :return: list of sorts group array table entries 
        """    
        arrays = []
        for name in self.ph5_obj.ph5_g_sorts.names():
            array_list, null = self.ph5_obj.ph5_g_sorts.read_arrays(name)
            for entry in array_list:
                arrays.append(entry)
                
        return arrays
    
    @property
    def das_station_map(self):
        """
        das_station_map originates from the different array tables in the 
        sorts group.  It is a list of dictionaries with entries
            
            * serial --> serial number of data logger
            * station --> station name
            * array_name --> name of array in sorts table
            
        :return: list of dictionaries
        
        .. note:: If there are no array entries returns and empty list
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
        
        :return: name of array table associated with the given station
        
        .. note:: station name should be verbatim or close
        """
        
        for entry in self.das_station_map:
            ### the entry is binary, need to decode into unicode
            if station in entry['station'].decode():
                return entry['array_name']
        return None
        
    def open_mini(self, mini_num):
        """
        Open a mini PH5 file with the name miniPH5_xxxxx.ph5
        
        :param mini_num: name of mini file to open
        
        :return: class: ph5.core.experiment, str: name
        """

        filename = "miniPH5_{0:05}.ph5".format(mini_num)
        mini_ph5_obj = experiment.ExperimentGroup(nickname=filename,
                                                  currentpath=self.ph5_path)
        mini_ph5_obj.ph5open(True)
        mini_ph5_obj.initgroup()
        
        return mini_ph5_obj, filename
     
    def get_current_mini_num(self, station, first_mini=1):
        """
        get the current mini number for the given station.
        
        :param str station: station name
        :param int first_mini: number of the first mini PH5 file
        
        :return: current mini number.
        
        """    
        mini_list = self.get_mini_list()
        if not mini_list:
            current_mini = first_mini
        else:
            current_mini = None 
            for mini in self.mini_map:
                for entry in self.das_station_map:
                    if (entry['serial'] in mini['das_list'] and
                            entry['station'] == station):
                        current_mini = mini['num']
                if not current_mini:
                    largest = 0
                    for station in self.mini_map:
                        if station['num'] >= largest:
                            largest = station['num']
                    if (mini['size'] < self.mini_size_max):
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
    
    @property
    def mini_map(self):
        """
        mini_map is a list of dictionaries describing properties of existing
        mini files with keys
        
            * num --> mini file number
            * das_list --> list of stations associated with that mini file
            * size --> size of mini file in bytes
        
        :return: list of dictionaries containing what mini file contains 
                 what serial #s
        """
        mini_map = []
        for mini_fn in self.get_mini_list():
            mini_num = int(mini_fn.split('.')[-2].split('_')[-1])
            exrec = experiment.ExperimentGroup(nickname=mini_fn)
            exrec.ph5open(True)
            exrec.initgroup()
            all_das = exrec.ph5_g_receivers.alldas_g()
            mini_size = self.get_mini_size(exrec.filename)
            das_list = []
            for g in all_das:
                name = g.split('_')[-1]
                das_list.append(name)
            mini_map.append({'num':mini_num,
                             'das_list':das_list,
                             'size':mini_size})
            exrec.ph5close()
            
        return mini_map   
    
    ### add survey metadata
    def add_survey_metadata(self, survey_dict):
        """
        add survey metdata to experiment table
        
        :param dict survey_dict: survey dictionary with keys 
        
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
        survey_dict = validate_time_metadata(survey_dict)
        
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
        Add a column to experiment table in case it doesn't exist
        
        :param str new_col_name: new column name
        :param str new_col_values: new column values
        :param str new_col_type: new column data type
        :param int type_len: length of new data type
        
        :return: new table with added columns
        
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
        sampling rate.  Therefore you need an array table for each station.
        Within this table you will need an array entry for every channel 
        collected for every run/schedule time for the given station.
        
        This is also the best place to add any metadata that isn't hard coded
        in apparently.
        
        ..note:: If the array name already exists it will just add another row
                 to the existing array table.
        
        :param str array_name: name of array --> Array_t_xxxxx
        
        :param dict array_dict: dictionary containing important metadata
        
        :return: array name
        
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
        array_dict = validate_time_metadata(array_dict)
        ### make new array in sorts table
        ### make a new sorts array table from given name
        if not array_name in self.ph5_obj.ph5_g_sorts.namesArray_t():
            self.ph5_obj.ph5_g_sorts.newArraySort(array_name)
        self.ph5_obj.ph5_g_sorts.populateArray_t(array_dict, name=array_name)
        
        return array_name
    
    def add_reciever_to_table(self, receiver_dict):
        """
        Add a receiver metadata to the receivers table
        
        :param dict receiver_dict: dictionary of metadata for single receiver
        
        ========================= ================================= ===========
        Key                       Description                       Type   
        ========================= ================================= ===========
        orientation/description_s orientation description           string
        azimuth/value_f           azimuth value in orientation      float
        azimuth/units_s           units of azimuth                  string
        dip/value_f               dip angle                         float
        dip/units_s               units of azimuth                  string 
        ========================= ================================= ===========
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
        
        :param str station_name: station name
        
        :return: das_group_name, mini_ph5_object
        """
        ### get mini number first
        mini_num = self.get_current_mini_num(station_name)
        mini_ph5_obj, filename = self.open_mini(mini_num)
        
        ### make sure there is a station group
        das_group = mini_ph5_obj.ph5_g_receivers.getdas_g(station_name)
        if not das_group:
            das_group, dt, rt, tt = mini_ph5_obj.ph5_g_receivers.newdas(station_name)
        mini_ph5_obj.ph5_g_receivers.setcurrent(das_group)
        
        return das_group, mini_ph5_obj
    
    def add_channel(self, mini_ph5_obj, station, array_dict, channel_array,
                    data_type='int32', description=None):
        """
        add channel to station mini PH5 file
        
        :param object mini_ph5_obj: mini PH5 object
        :param str station: station name
        :param array channel_array: data array
        :param dict channel_meta_dict: channel 
            
        """
        array_dict = validate_time_metadata(array_dict)
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
        
        ### get channel dictionary from array metadata
        channel_dict = self.make_channel_entry(array_dict)
        channel_dict['sample_count_i'] = len(channel_array)
        
        ### add the appropriate array name to the metadata
        channel_dict['array_name_data_a'] = data_array_name
        
        ### create new data array
        mini_ph5_obj.ph5_g_receivers.newarray(channel_dict['array_name_data_a'],
                                              channel_array,
                                              dtype=data_type,
                                              description=description)
        
        ### add the channel metadata to the das table
        mini_ph5_obj.ph5_g_receivers.populateDas_t(channel_dict)
        
        ### add channel metadata to appropriate sorts array
        sorts_array_name = self.get_sort_array_name(station)
        self.add_array_to_sorts(sorts_array_name, array_dict)
        
        ### make time index entry
        t_index_entry = self.make_time_index_entry(array_dict,
                                                   mini_ph5_obj.nickname)
        self.ph5_obj.ph5_g_receivers.populateIndex_t(t_index_entry)
        
        ### update external references
        self.update_external_reference(t_index_entry)
        
        return t_index_entry
    
    def make_channel_entry(self, meta_dict):
        """
        make a channel dictionary from array dictionary 
        
        :param dict meta_dict: array channel metadata from sorts group
        
        .. seealso:: add_array_to_sorts
        
        Makes a dictionary with keys
        
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
        channel_dict = {}
        for t_key in t_list:
            channel_dict['time/{0}'.format(t_key)] = meta_dict['deploy_time/{0}'.format(t_key)]
        for key in ['sample_rate_i', 'sample_rate_multiplier_i', 'channel_number_i']:
            channel_dict[key] = meta_dict[key]
            
        ### add response table entry number to metadata
        channel_dict['response_table_n_i'] = self.get_response_n(meta_dict['id_s'],
                    channel_dict['sample_rate_i'],
                    channel_dict['channel_number_i'])
        ### add receiver table entry number to metadata
        channel_dict['receiver_table_n_i'] = self.get_receiver_n(meta_dict['id_s'],
                    channel_dict['sample_rate_i'],
                    channel_dict['channel_number_i'])
        
        return channel_dict
    
    def make_time_index_entry(self, meta_dict, mini_name):
        """
        make a time index entry
        """
        
        entry_dict = {}
        entry_dict['serial_number_s'] = meta_dict['id_s']
        for t_key in t_list:
            entry_dict['start_time/{0}'.format(t_key)] = meta_dict['deploy_time/{0}'.format(t_key)]
            entry_dict['end_time/{0}'.format(t_key)] = meta_dict['pickup_time/{0}'.format(t_key)]
    
        ### make time stamp
        now = datetime.datetime.now(datetime.timezone.utc)
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
        for count, array_entry in enumerate(self.get_arrays(), 1):
            if (array_entry['sample_rate_i'] == sample_rate and
                array_entry['channel_number_i'] == channel_number and
                array_entry['id_s'] == station):
                return array_entry['receiver_table_n_i']
        return len(self.get_arrays())
    
    def get_response_n(self, station, sample_rate, channel_number):
        """
        get receiver table index for given station, given channel
        """
        # figure out receiver and response n_i
        for count, array_entry in enumerate(self.get_arrays(), 1):
            if (array_entry['sample_rate_i'] == sample_rate and
                array_entry['channel_number_i'] == channel_number and
                array_entry['id_s'] == station):
                return array_entry['response_table_n_i']
        return len(self.get_arrays())



    
## =============================================================================
## Tests    
## =============================================================================
#ph5_fn = r"c:\Users\jpeacock\Documents\GitHub\PH5_py3\ph5\test_data\test.ph5"
#survey_json = r"c:\Users\jpeacock\Documents\GitHub\mt2ph5\survey_metadata.json"
#station_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\station_metadata.json"
#receiver_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\receiver_metadata.json"
#channel_json = r"C:\Users\jpeacock\Documents\GitHub\mt2ph5\channel_metadata.json"
#
#if os.path.exists(ph5_fn):
#    os.remove(ph5_fn)
#
#ph5_test_obj = generic2ph5()
#ph5_test_obj.open_ph5_file(ph5_fn)
#
#### first step is to add general information about the survey as metadata
#### this goes into the Experiment Group/Experiment_table
#### add Survey metadata to file
#survey_dict = load_json(survey_json)
#ph5_test_obj.add_survey_metadata(survey_dict)
#
#### How to add a station
#### A station basically makes its own mini ph5 which has its own experiment
#### group.  The Receivers group is where the metadata goes for the station.
#### The channel data will go into this group as well
##### add station
#das_group_name, mini_ph5_obj = ph5_test_obj.add_station_mini('mt01')
#
#### How to add channel data
#### Add a channel metadata to the master ph5 receivers table
##### add channel data
#### 1 -- add receiver to table
#receiver_dict = load_json(receiver_json)
#n_receiver = ph5_test_obj.add_reciever_to_table(receiver_dict)
#
#### Add channel specifice metadata to the master sorts group as an array that
#### is linked to the specific station.
#### 2 -- add array to sorts
#array_dict = load_json(station_json)
#array_dict['receiver_table_n_i'] = n_receiver
#new_array = ph5_test_obj.add_array_to_sorts(ph5_test_obj.ph5_obj.ph5_g_sorts.nextName(),
#                                            array_dict)
#
#### Add the data to the station ph5 into 
#### 3 -- add array data
#channel_dict = load_json(channel_json)
#t_entry = ph5_test_obj.add_channel(mini_ph5_obj, 'mt01', array_dict, 
#                                   np.random.randint(2**12, size=2**16,
#                                                     dtype=np.int32))
def get_seed_band_code(sampling_rate):
    """
    get the seed band code based on sampling rate
    F	…	≥ 1000 to < 5000	≥ 10 sec
    G	…	≥ 1000 to < 5000	< 10 sec
    D	…	≥ 250 to < 1000	< 10 sec
    C	…	≥ 250 to < 1000	≥ 10 sec
    E	Extremely Short Period	≥ 80 to < 250	< 10 sec
    S	Short Period	≥ 10 to < 80	< 10 sec
    H	High Broad Band	≥ 80 to < 250	≥ 10 sec
    B	Broad Band	≥ 10 to < 80	≥ 10 sec
    M	Mid Period	> 1 to < 10	
    L	Long Period	≈ 1	
    V	Very Long Period	≈ 0.1	
    U	Ultra Long Period	≈ 0.01	
    R	Extremely Long Period	≥ 0.0001 to < 0.001	
    P	On the order of 0.1 to 1 day 1	≥ 0.00001 to < 0.0001	
    T	On the order of 1 to 10 days 1	≥ 0.000001 to < 0.00001	
    Q	Greater than 10 days 1	< 0.000001	
    A	Administrative Instrument Channel	variable	NA
    O	Opaque Instrument Channel	variable	NA
    """
    code = 'A'
    if sampling_rate >= 1000 and sampling_rate < 5000:
        code = 'F'
    elif sampling_rate >= 250 and sampling_rate < 1000:
        code = 'D'
    elif sampling_rate >= 80 and sampling_rate < 250:
        code = 'E'
    elif sampling_rate >= 10 and sampling_rate < 80:
        code = 'B'
    elif sampling_rate > 1 and sampling_rate < 10:
        code = 'M'
    elif sampling_rate == 1:
        code = 'L'
    elif sampling_rate == 0.1:
        code = 'V'
    elif sampling_rate == 0.01:
        code = 'U'
    elif sampling_rate >= 0.0001 and sampling_rate < 0.001:
        code = 'R'
    elif sampling_rate >= 0.00001 and sampling_rate < 0.0001:
        code = 'P'
    elif sampling_rate >= 0.000001 and sampling_rate < 0.00001:
        code = 'T'
    elif sampling_rate < .000001:
        code = 'Q'
        
    return code
    
def get_seed_instrument_code(component):
    """
    seed instrument code
    """
    code = 'N'
    if 'e' in component.lower():
        code =  'Q'
    elif 'h' in component.lower():
        code = 'F'
    return code

def get_seed_orientation_code(component):
    """
    seed orientation code
    
    Z N E	Traditional (Vertical, North-South, East-West)
    1 2 3	Orthogonal components but non traditional orientations
    """
    code = None
    if component.lower() in ['ex', 'hx']:
        code = '1'
    elif component.lower() in ['ey', 'hy']:
        code = '2'
    elif component.lower() in ['hz']:
        code = 'Z'
    return code
            
    
        

