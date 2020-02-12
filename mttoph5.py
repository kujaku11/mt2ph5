"""
Put MT time series into PH5 format following the example from Obspy written
by Derick Hess

Using mtpy package to read in MT time series in Z3D format, but could extend
that to any type of time series later.

J. Peacock
June-2019
"""
# =============================================================================
# Imports
# =============================================================================
import logging
import os
import re
import glob
#import pathlib
import ph5_tools
from ph5.core import experiment, columns
from mtpy.core import ts as mtts
from mtpy.usgs import zen
from mtpy.usgs import nims
### inheret ph5_tools.generic to_ph5
#from mt2ph5 import ph5_tools


PROG_VERSION = '2019.65'
# logger = logging.getLogger(__name__)

# =============================================================================
# Class
# =============================================================================
class MTtoPH5Error(Exception):
    """
    Exception raised when there is a problem with the request.
    :param: message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message

class MTtoPH5(ph5_tools.generic2ph5):
    """
    Load in MT time series to PH5 format.  
    
    Currently can read in Z3D or ascii files and gets metadata from those files  
    
    :param ph5_object: Main PH5 object to add files to
    :type ph5_object: PH5.core.experiment
    
    :param ph5_path: full path to PH5 file minus the extension
    :type ph5_path: string
    
    :param num_mini: number of mini files to make
    :type num_mini: int
    
    :param first_mini: number of first mini file
    :type first_mini: int
    
    .. note:: For now the organization is:
              * Experiment
                  - MT station 01 
                      * Schedule or Run 01
                          - EX, EY, HX, HY, HZ
                      * Schedule or Run 02
                          - EX, EY, HX, HY, HZ
                  - MT station 02 
                      * Schedule or Run 01
                          - EX, EY, HX, HY, HZ
                      * Schedule or Run 02
                          - EX, EY, HX, HY, HZ
                          
    :Example: ::
        
        >>> ph5_fn = r"./test_ph5.ph5"
        >>> fn_list = glob.glob(r"/home/mt_files/*.Z3D")
        >>> ### initialize a PH5 object
        >>> ph5_obj = experiment.ExperimentGroup(nickname='test_ph5',
        >>> ...                           currentpath=os.path.dirname(ph5_fn))
        >>> ph5_obj.ph5open(True)
        >>> ph5_obj.initgroup()
        >>> ### initialize mt_to_ph5 object want only 1 mini file starting at 1
        >>> mt_obj = MTtoPH5(ph5_obj, os.path.dirname(ph5_fn), 1, 1)
        >>> # turn on verbose logging so we can see more info
        >>> mt_obj.verbose = True
        >>> # only do the first 5 files because that is one schedule or run
        >>> message, index_t = mt_obj.to_ph5(fn_list[0:5])
        >>> # now load are index table
        >>> for entry in index_t:
        >>>     ph5_obj.ph5_g_receivers.populateIndex_t(entry)
        >>> 
        >>> # the last thing we need ot do ater loading
        >>> # all our data is to update external refeerences
        >>> # this takes all the mini files and adds their
        >>> # references to the master so we can find the data
        >>> mt_obj.update_external_references(index_t)
        >>>  
        >>> # be nice and close the file
        >>> ph5_obj.ph5close()                   
    """
    

    def __init__(self, ph5_object=None,
                 ph5_path=None,
                 num_mini=1,
                 first_mini=1):
        """
        :param ph5_object: Main PH5 object to add files to
        :type ph5_object: PH5.core.experiment
        
        :param ph5_path: full path to PH5 file minus the extension
        :type ph5_path: string
        
        :param num_mini: number of mini files to make
        :type num_mini: int
        
        :param first_mini: number of first mini file
        :type first_mini: int
        """
        super().__init__()
        self.num_mini = num_mini
        self.first_mini = first_mini
        self.logger = logging.getLogger('MTtoPH5')
        self.array_table = None
        
        self.time_t = list()
        
    def make_index_t_entry(self, ts_obj):
        """
        make a time index dictionry (index_t_entry) for a given time series.
        
        :param ts_obj: MTTS time-series object
        :returns: dictionary of necessary values
        """
        index_t_entry = {}
        # start time
        index_t_entry['start_time/ascii_s'] = (ts_obj.start_time_utc)
        index_t_entry['start_time/epoch_l'] = (int(ts_obj.start_time_epoch_sec))
        index_t_entry['start_time/micro_seconds_i'] = (ts_obj.ts.index[0].microsecond)
        index_t_entry['start_time/type_s'] = 'BOTH'
        
        # end time
        index_t_entry['end_time/ascii_s'] = (ts_obj.stop_time_utc)
        index_t_entry['end_time/epoch_l'] = (int(ts_obj.stop_time_epoch_sec))
        index_t_entry['end_time/micro_seconds_i'] = (ts_obj.ts.index[-1].microsecond)
        index_t_entry['end_time/type_s'] = 'BOTH'
        
        # time stamp -- when data was entered
        time_stamp_utc = mtts.datetime.datetime.utcnow()
        index_t_entry['time_stamp/ascii_s'] = (time_stamp_utc.isoformat())
        index_t_entry['time_stamp/epoch_l'] = (int(time_stamp_utc.timestamp()))
        index_t_entry['time_stamp/micro_seconds_i'] = (time_stamp_utc.microsecond)
        index_t_entry['time_stamp/type_s'] = 'BOTH'
        
        index_t_entry['serial_number_s'] = ts_obj.data_logger
        index_t_entry['external_file_name_s'] = ''
        
        return index_t_entry
    
    def make_receiver_t_entry(self, ts_obj):
        """
        make receiver table entry
        """
        
        receiver_t_entry = {}
        receiver_t_entry['orientation/azimuth/value_f'] = ts_obj.azimuth
        receiver_t_entry['orientation/azimuth/units_s'] = 'degrees'
        receiver_t_entry['orientation/dip/value_f'] = 0
        receiver_t_entry['orientation/dip/units_s'] = 'degrees'
        receiver_t_entry['orientation/description_s'] = ts_obj.component
        receiver_t_entry['orientation/channel_number_i'] = ts_obj.channel_number
        receiver_t_entry['location/length/value_f'] = ts_obj.dipole_length
        receiver_t_entry['location/length/units_s'] = 'm'
        receiver_t_entry['location/x/units_s'] = 'm'
        receiver_t_entry['location/x/value_f'] = 0
        receiver_t_entry['location/y/units_s'] = 'm'
        receiver_t_entry['location/y/value_f'] = 0
        receiver_t_entry['location/z/units_s'] = 'm'
        receiver_t_entry['location/z/value_f'] = 0
        
        return receiver_t_entry
        
    def make_das_entry(self, ts_obj):
        """
        Make a metadata array for a given mtts object
        
        :param ts_obj: MTTS object
        :return: dictionary of das information
        """
        das_entry = {}
        # start time information
        das_entry['time/ascii_s'] = ts_obj.start_time_utc
        das_entry['time/epoch_l'] = int(ts_obj.start_time_epoch_sec)
        das_entry['time/micro_seconds_i'] = ts_obj.ts.index[0].microsecond
        das_entry['time/type_s'] = 'BOTH'
        
        das_entry['sample_rate_i'] = ts_obj.sampling_rate
        das_entry['sample_rate_multiplier_i'] = 1
        
        das_entry['channel_number_i'] = ts_obj.channel_number
        das_entry['sample_count_i'] = ts_obj.n_samples
        das_entry['raw_file_name_s'] = ts_obj.fn
#        das_entry['component_s'] = ts_obj.component.upper()
#        das_entry['dipole_length_f'] = ts_obj.dipole_length
#        das_entry['dipole_length_units_s'] = 'meters'
#        das_entry['sensor_id_s'] = ts_obj.channel_number
#        das_entry['array_name_data_a'] = '{0}_{1}_{2}'.format('Data',
#                                                        ts_obj.component,
#                                                        '1')
        
        return das_entry
    
    def make_array_entry(self, ts_obj):
        """
        Make an array entry that will go into the sorts group of the main 
        Experiment object.
        > Sorts_g
        > Array_t_xxx [The array tables contain receiver geometry and metadata.]
           id_s [string 16] - ID related to sensor collecting data
           channel_number_i [int 8] - channel number
           description_s [string 1024] - description of time-series data
           seed_band_code_s [string 8] - ?  
           seed_instrument_code_s [string 8] - ?
           seed_orientation_code_s [string 8] - ? 
           seed_location_code_s [string 8] - ?
           seed_station_name_s [string 16] - ?
           sample_rate_i [int 16] -  sample rate of time series (samples/s)
           sample_rate_multiplier [int 16] - sample rate multiplier
           receiver_table_n_i [int 32] - receiver table lookup number?
           response_table_n_i [int 32] - response table look up number?
           location - location of sensor
               coordinate_system_s [string 32] - coordinate system
               projection_s [string 32] - projection
               ellipsoid_s [string 32] - ellipsoid
               description_s [string 1024] -description of location
               X 
                   value_d [float 64] - value of x location 
                   units_s [string 16] - units of x location
               Y
                   value_d [float 64] - value of y location
                   units_s [string 16] - units of y location
               Z
                   value_d [float 64] - value of z location
                   units_s [string 16] - units of z location
           deploy_time - time at which station was set up?
               ascii_s [string 32] - isorormat time string
               epoch_l [int 64] - epoch seconds of deploy time
               micro_seconds_i [int 32] - micro seconds of 
               type_s [string 8] -Epoch, UTC, Both
           pickup_time - time at which sensor was picked up
               ascii_s [string 32] - isoformat pick up time string
               epoch_l [int 64] - epoch seconds pick up time 
               micro_seconds_i [int 32] - microseconds
               type_s [string 8] - Epoch, UTC, both
           das - digital aquisition system
               serial_number_s [string 64] - serial number
               model_s [string 64] - model 
               manufacturer_s [string 64] - manufacturer
               notes_s [string 1024] - notes on DAS
           sensor - measuring sensor
               serial_number_s [string 64] - serial number of sensor
               model_s [string 64] - model 
               manufacturer_s [string 64] - manufacturer
               notes_s [string 1024] - notes on sensor
        
        """
        array_entry = {}
        array_entry['id_s'] = ts_obj.station
        array_entry['channel_number_i'] = ts_obj.channel_number
        array_entry['description_s'] = ts_obj.component
        array_entry['seed_band_code_s'] = ph5_tools.get_seed_band_code(ts_obj.sampling_rate)
        array_entry['seed_instrument_code_s'] = ph5_tools.get_seed_instrument_code(ts_obj.component)
        array_entry['seed_orientation_code_s'] = ph5_tools.get_seed_orientation_code(ts_obj.component)
        array_entry['seed_location_code_s'] = ''
        array_entry['seed_station_name_s'] = ''
        array_entry['sample_rate_i'] = ts_obj.sampling_rate
        array_entry['sample_rate_multiplier_i'] = 1
        array_entry['receiver_table_n_i'] = self.get_receiver_n(ts_obj.station,
                                                                ts_obj.sampling_rate,
                                                                ts_obj.channel_number)
        array_entry['response_table_n_i'] = self.get_response_n(ts_obj.station,
                                                                ts_obj.sampling_rate,
                                                                ts_obj.channel_number)
        array_entry['location/coordinate_system_s'] = 'Geographic'
        array_entry['location/projection_s'] = 'WGS84'
        array_entry['location/ellipsoid_s'] = ''
        array_entry['location/description_s'] = ''
        array_entry['location/X/value_d'] = ts_obj.lon
        array_entry['location/X/units_s'] = 'degrees'
        array_entry['location/Y/value_d'] = ts_obj.lat
        array_entry['location/Y/units_s'] = 'degrees'
        array_entry['location/Z/value_d'] = ts_obj.elev
        array_entry['location/Z/units_s'] = 'meters'
        array_entry['deploy_time/ascii_s'] = ts_obj.start_time_utc
        array_entry['deploy_time/epoch_l'] = int(ts_obj.start_time_epoch_sec)
        array_entry['deploy_time/micro_seconds_i'] = ts_obj.ts.index[0].microsecond
        array_entry['deploy_time/type_s'] = 'BOTH'
        array_entry['pickup_time/ascii_s'] = ts_obj.stop_time_utc
        array_entry['pickup_time/epoch_l'] = int(ts_obj.stop_time_epoch_sec)
        array_entry['pickup_time/micro_seconds_i'] = ts_obj.ts.index[-1].microsecond
        array_entry['pickup_time/type_s'] = 'BOTH'
        array_entry['das/serial_number_s'] = ts_obj.data_logger
        array_entry['das/model_s'] = ts_obj.data_logger 
        array_entry['das/manufacturer_s'] = 'NAROD'
        array_entry['das/notes_s'] = ''
        array_entry['sensor/serial_number_s'] = '1111'
        array_entry['sensor/model_s'] = 'sensor_model' 
        array_entry['sensor/manufacturer_s'] = ''
        array_entry['sensor/notes_s'] = ''
        
        return array_entry
    
    def make_sort_entry(ts_obj):
        """
        Make a sorts entry
        
        > Sort_t (sorts table)
            event_id_s [string 16] - even ID
            array_name_s [string 16] - array name
            array_t_name_s [string 16] - array table name
            description_s [string 1024] - description of array
            start_time - start time of data collection 
                ascii_s [string 32] - isoformat time string
                epoch_l [int 64] - epoch seconds 
                micro_seconds_i [int 32] - micro seconds
                type_s [string 8] - Epoch, UTC, Both
            end_time - end time of data collections
                ascii_s [string 32] - isoformat time string
                epoch_l [int 64] - epoch seconds
                micro_seconds_i [int 32] - micro seconds
                type_s [string 8] - Epoch, UTC, Both
            time_stamp - time downloaded?     
                ascii_s [string 32] - isoformat time string
               epoch_l [int 64] - epoch seconds
               micro_seconds_i [int 32] - microseconds
               type_s [string 8] - Epoch, UTC, Both
        """
        
    
    def load_ts_obj(self, ts_fn):
        """
        load an MT file
        """
        if isinstance(ts_fn, str):
            ext = os.path.splitext(ts_fn)[-1][1:].lower()
            if ext == 'z3d':
                self.logger.info('Opening Z3D file {0}'.format(ts_fn))
                z3d_obj = zen.Zen3D(ts_fn)
                z3d_obj.read_z3d()
                ts_obj = z3d_obj.ts_obj
            elif ext in ['ex', 'ey', 'hx', 'hy', 'hz']:
                self.logger.info('Opening ascii file {0}'.format(ts_fn))
                ts_obj = mtts.MTTS()
                ts_obj.read_file(ts_fn)
            elif ext in  ['bnn', 'bin']:
                self.logger.info('Opening NIMS file {0}'.format(ts_fn))
                nims_obj = nims.NIMS(ts_fn)
                ts_obj = [nims_obj.hx, nims_obj.hy, nims_obj.hz, nims_obj.ex, 
                          nims_obj.ey]
                
        elif isinstance(ts_fn, mtts.MTTS):
            ts_obj = ts_fn
            self.logger.info('Loading MT object')
        else:
            raise mtts.MTTSError("Do not understand {0}".format(type(ts_fn)))
            
        return ts_obj
    
    def get_current_das(self, ph5_object, data_logger):
        """
        get the current DAS table from a PH5 object
        """
        # get node reference or create new node
        das_table = ph5_object.ph5_g_receivers.getdas_g(data_logger)
        if not das_table:
            das_table, t, r, ti = ph5_object.ph5_g_receivers.newdas(data_logger)
            
        return das_table
    
    def single_ts_to_ph5(self, ts_obj, count=1):
        """
        load a single time series into ph5
        """
        ### start populating das table and data arrays
        index_t_entry = self.make_index_t_entry(ts_obj)
        das_t_entry = self.make_das_entry(ts_obj)
        receiver_t_entry = self.make_receiver_t_entry(ts_obj)
        array_t_entry = self.make_array_entry(ts_obj)
        
        ### add receiver entry number
        das_t_entry['receiver_table_n_i'] = self.get_receiver_n(ts_obj.station,
                                                                ts_obj.sampling_rate,
                                                                ts_obj.channel_number)
        das_t_entry['response_table_n_i'] = count
        
        ### get the current mini file
        current_mini = self.get_current_mini_num(ts_obj.data_logger)
        mini_handle, mini_name = self.open_mini(current_mini)
        
        current_das_table_mini = self.get_current_das(mini_handle,
                                                      ts_obj.data_logger)
        mini_handle.ph5_g_receivers.setcurrent(current_das_table_mini)
        
        ### make name for array data going into mini file
        while True:
            next_ = '{0:05}'.format(count)
            das_t_entry['array_name_data_a'] = "Data_a_{0}".format(next_)
            node = mini_handle.ph5_g_receivers.find_trace_ref(das_t_entry['array_name_data_a'])
            if not node:
                break
            count = count + 1
            continue
        
        ### make a new array
        mini_handle.ph5_g_receivers.newarray(das_t_entry['array_name_data_a'],
                                             ts_obj.ts.data,
                                             dtype=ts_obj.ts.data.dtype,
                                             description=None)
        
        ### create external file names
        index_t_entry['external_file_name_s'] = "./{}".format(mini_name)
        das_path = "/Experiment_g/Receivers_g/Das_g_{0}".format(ts_obj.data_logger)
        index_t_entry['hdf5_path_s'] = das_path
        
        ### populate metadata tables 
        ### DAS goes in both mini and main
        mini_handle.ph5_g_receivers.populateDas_t(das_t_entry)
        
        current_das_table_main = self.get_current_das(self.ph5_obj, 
                                                      ts_obj.data_logger)
        self.ph5_obj.ph5_g_receivers.setcurrent(current_das_table_main)
        self.ph5_obj.ph5_g_receivers.populateDas_t(das_t_entry)
        ### index and receivers goes in main
        self.ph5_obj.ph5_g_receivers.populateIndex_t(index_t_entry)
        self.ph5_obj.ph5_g_receivers.populateReceiver_t(receiver_t_entry)
        #mini_handle.ph5_g_receivers.populateTime_t_()
        columns.populate(self.array_table, array_t_entry)

        # Don't forget to close minifile
        mini_handle.ph5close()
        
        self.logger.info('Loaded {0} to mini file {1}'.format(ts_obj.fn, 
                         mini_name))
        
        return count
        

    def to_ph5(self, ts_list):
        """
        Takes a list of either files or MTTS objects and puts them into a 
        PH5 file.
        
        :param ts_list: list of filenames (full path) or ts objects
        :returns: success message
        """
        if self.array_table is None:
            self.array_table = self.ph5_obj.ph5_g_sorts.newArraySort('Array_t_001')

        # check if we are opening a file or mt ts object
        for count, fn in enumerate(ts_list, 1):
            ts_obj = self.load_ts_obj(fn)
            if isinstance(ts_obj, list):
                for single_ts_obj in ts_obj:
                    count = self.single_ts_to_ph5(single_ts_obj, count)
            else:
                count = self.single_ts_to_ph5(ts_obj, count)
        
        return "done"

# =============================================================================
# Test
# =============================================================================
#ts_fn = r"c:\Users\jpeacock\Documents\GitHub\sandbox\ts_test.EX"
ph5_fn = r"c:\Users\jpeacock\Documents\test_ph5.ph5"
nfn = r"c:\Users\jpeacock\OneDrive - DOI\MountainPass\FieldWork\LP_Data\Mnp300a\DATA.BIN"

#fn_list = glob.glob(r"c:\Users\jpeacock\Documents\imush\O015\*.Z3D")

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
mt_obj = MTtoPH5()
mt_obj.ph5_obj = ph5_obj

# we give it a our trace and should get a message
# back saying done as well as an index table to be loaded
message = mt_obj.to_ph5([nfn])

# now load are index table
# the last thing we need ot do ater loading
# all our data is to update external refeerences
# this takes all the mini files and adds their
# references to the master so we can find the data
# for entry in index_t:
#     ph5_obj.ph5_g_receivers.populateIndex_t(entry)
#     mt_obj.update_external_reference(entry)

# be nice and close the file
ph5_obj.ph5close()
