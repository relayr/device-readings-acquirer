"""
Relayr To InfluxDB Inflater v1.0.0

This script is a bridge between the relayr cloud and a local instance of InfluxDB.
It downloads the data of a certain device and store them in local.

Last Edit: 06 Dec 2016 11.40

Copyright Riccardo Marconcini (riccardo DOT marconcini AT relayr DOT de)
"""


#######################################################################################################################
#   Libraries, Modules & API                                                                                          #
#######################################################################################################################

import argparse
import time
import shelve
from relayr.api import Api
from influxdb import InfluxDBClient


#######################################################################################################################
#   Global Parameters                                                                                                 #
#######################################################################################################################

TOKEN = ""
DEVICE_ID = ""
DB_NAME = ""
FREQ_CHECKING = 0
HOST = ""
PORT = 0
NORM = 0


#######################################################################################################################
#   Main                                                                                                              #
#######################################################################################################################

def main():
    """ Main function is an endless loop. First it checks if there is a timestamp of the last downloaded reading, then
        it query the relayr cloud if there are new readings. Then it parses the result JSON and insert the reading in
        InfluxDB database.
    :return: None
    """

    while True:

        #   Control of the last timestamp
        try:
            last_timestamp = get_last_timestamp()
        except:
            print("Last timestamp not found. Setting as default three days ago...")
            last_timestamp = (current_milli_time() - 259200000)
        print("Last Timestamp: ", last_timestamp)

        #   Loop that checks if History API are correctly running and then it gets the readings of a device from a
        #   certain timestamp
        while True:
            try:
                time.sleep(5)
                api = Api(TOKEN)
                print("Start downloading data")
                history = api.get_history_devices(DEVICE_ID, last_timestamp, None, None, None, None, None, None)
                break
            except:
                history = []
                print("API error... retry.")

        #   Loop for checking if InfluxDB is running, exit from the loop when the InfluxDB Client is established
        while True:
            try:
                time.sleep(5)
                influxClient = InfluxDBClient(HOST, PORT, "root", "root")
                influxClient.create_database(DB_NAME)   # if the database is already existing, the creation is skipped
                print("Connection to InfluxDB established")
                break
            except:
                print("Database not ready... retry.")

        data = []
        count = 0

        #  Parsing the JSON data from relayr into a format readable for InfluxDB
        try:
            for i in range(len(history['results'])):
                for k in range(len(history['results'][i]['points'])):
                    data.append({
                        'measurement': history['results'][i]['meaning'],
                        'time': history['results'][i]['points'][k]['timestamp'],
                        'fields': {'value': history['results'][i]['points'][k]['value']/NORM}
                    })
                    count += 1
                    tmp_last_timestamp = history['results'][i]['points'][k]['timestamp']

            #   Writing the data parsed into the database specified as parameter
            try:
                influxClient.write_points(data, database=DB_NAME, time_precision="ms")
                print("Added ", count, " new rows in database")
                if count > 0:
                    # increasing the timestamp of 1ms before save to avoid to insert again that reading during next
                    # iteration
                    set_last_timestamp(tmp_last_timestamp+1)
                    print("New Last Timestamp: ", tmp_last_timestamp+1)
            except Exception as e:
                print(e)
        except:
            print("Error Writing")

        print("Sleeping for the next ", FREQ_CHECKING, " seconds... \n")
        time.sleep(FREQ_CHECKING)


#######################################################################################################################
#   Functions                                                                                                         #
#######################################################################################################################

#   Set function for the last timestamp using the shelf module
def set_last_timestamp(timestamp):
    """ The function saves a timestamp through the shelve module into a file called history_downloader_setting under
        the key settings as last_timestamp
    :param timestamp: int
    :return: None
    """
    s = shelve.open('history_downloader_settings')
    try:
        s['settings'] = {'last_timestamp': timestamp}
    except:
        print("Impossible to create settings file")
    finally:
        s.close()


#   Get function for the last timestamp using the shelf module
def get_last_timestamp():
    """ The function open the file history_downloader_settings through the shelve module and get the value contained
        as last_timestamp under the key settings
    :return: int
    """
    s = shelve.open('history_downloader_settings')
    try:
        existing = s['settings']['last_timestamp']
    finally:
        s.close()
    return existing


#   Return current time in milliseconds
def current_milli_time():
    return int(round(time.time() * 1000))


#######################################################################################################################
#   Parsing Command Line Args                                                                                         #
#######################################################################################################################

def parse_args():
    """ The function parse the args specified in the CLI
    :return: parsed args
    """
    parser = argparse.ArgumentParser(description="History Downloader from relayr cloud to InfluxDB")
    parser.add_argument('--db', type=str, required=True, default="", help="Name of database")
    parser.add_argument('--freq', type=int, required=False, default=60, help="Frequency of checking the cloud, in s")
    parser.add_argument('--host', type=str, required=False, default="localhost", help="Hostname of InfluxDB")
    parser.add_argument('--port', type=int, required=False, default=8086, help="Port of InfluxDB")
    parser.add_argument('--token', type=str, required=True, default="", help="Token in relayr dashboard")
    parser.add_argument('--device', type=str, required=True, default=0, help="Device")
    parser.add_argument('--norm', type=int, required=False, default=1, help="Normalization value to divide the reading")
    return parser.parse_args()


#######################################################################################################################
#   Calling Main Function                                                                                             #
#######################################################################################################################

if __name__ == '__main__':
    args = parse_args()
    TOKEN = args.token
    DEVICE_ID = args.device
    DB_NAME = args.db
    FREQ_CHECKING = args.freq
    HOST = args.host
    PORT = args.port
    NORM = args.norm
    main()
