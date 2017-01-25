"""
Relayr to InfluxDB History Downloader v2.1.0

This script is a bridge between the Relayr cloud and a local instance of InfluxDB.
It downloads the data of a certain device and store them in local.

Last Edit: 25 Jan 2017 18.36 CET

Copyright Riccardo Marconcini (riccardo DOT marconcini AT relayr DOT de)

TODO: add how many rows are added for each meaning
TODO: renew token
"""


#######################################################################################################################
#   Libraries, Modules & API                                                                                          #
#######################################################################################################################

import argparse
import time
import shelve
import requests
from datetime import datetime
import calendar
from influxdb import InfluxDBClient


#######################################################################################################################
#   Global Variables                                                                                                  #
#######################################################################################################################

TOKEN = ""
DEVICE_ID = ""
DB_NAME = ""
FREQ_CHECKING = 0
HOST = ""
STARTING_TIMESTAMP = 0
PORT = 0
NORM = 1


#######################################################################################################################
#   Main                                                                                                              #
#######################################################################################################################

def main():
    """ Main function is an endless loop. First it checks if there is a timestamp of the last downloaded reading, then
        it queries the relayr cloud if there are new readings. Then it parses the result JSON and insert the reading in
        InfluxDB database.
    :return: None
    """

    while True:

        data = []
        count = 0
        tmp_last_timestamp = 0

        #   Control of the last timestamp or the given one if parsed arg
        try:
            if STARTING_TIMESTAMP != 0:
                last_timestamp = STARTING_TIMESTAMP
            else:
                last_timestamp = get_last_timestamp()
        except:
            print("Last timestamp not found. Setting as default three days ago...")
            last_timestamp = (current_milli_time() - 259200000)
        print("Last Timestamp: ", last_timestamp)

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

        while True:
            try:
                print("Start downloading data")

                time.sleep(5)

                #   Request the device info to retrieve the model ID
                device_info = requests.get('https://api.relayr.io/devices/' + DEVICE_ID,
                                           headers={"authorization": "Bearer " + TOKEN,
                                                    "cache-control": "no-cache"})
                device_info_json = device_info.json()

                #   Request the model ID to retrieve the meanings
                model_info = requests.get('https://api.relayr.io/device-models/' + device_info_json['modelId'],
                                          headers={"authorization": "Bearer " + TOKEN,
                                                   "cache-control": "no-cache"})
                model_info_json = model_info.json()
                meanings = []
                for i in range(len(model_info_json['firmware']['1.0.0']['transport']['cloud']['readings'])):
                    meanings.append(model_info_json['firmware']['1.0.0']['transport']['cloud']['readings'][i]['meaning'])

                if len(last_timestamp) > 11:
                    start_timestamp_iso = last_timestamp
                else:
                    start_timestamp_iso = to_iso(last_timestamp)

                #   For every meaning the script performs a request to history API 2 and parse the readings into the
                #   data var
                for i in range(len(meanings)):
                    readings = requests.get('https://api.relayr.io/devices/' + DEVICE_ID
                                            + '/aggregated-readings?meaning=' + meanings[i]
                                            + '&start=' + start_timestamp_iso
                                            + '&interval=10s&aggregates=avg',
                                            headers={"authorization": "Bearer " + TOKEN, "accepted": "application/json"})
                    readings_json = readings.json()

                    for k in range(len(readings_json['data'])):
                        data.append({
                            'measurement': meanings[i],
                            'time': readings_json['data'][k]['timestamp'],
                            'fields': {'value': readings_json['data'][k]['avg']/NORM}
                        })
                        count += 1
                        tmp_last_timestamp = readings_json['data'][k]['timestamp']
                break
            except:
                print("Error with API... retry.")
                meanings = []
                data = []

        #   Writing the data parsed into the database specified as parameter
        try:
            influxClient.write_points(data, database=DB_NAME, time_precision="ms")
            print("Added ", count, " new rows in database")
            if count > 0:
                #   Increasing the timestamp of 1ms before save to avoid to insert again that reading during next
                #   iteration

                tmp_unix = to_unix(tmp_last_timestamp)
                set_last_timestamp(tmp_unix+1)
                print("New Last Timestamp: ", tmp_unix+1)
        except:
            print("Error Writing")

        #   Reset the START_TIME, if the script is launched with --timestamp, it is used only for the first iteration
        reset_starttime()

        #   Sleep
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
        s[DB_NAME] = {'last_timestamp': timestamp}
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
        existing = s[DB_NAME]['last_timestamp']
    finally:
        s.close()
    return existing


#   Return current time in milliseconds
def current_milli_time():
    """ Generate the current timestamp into milliseconds
    :return: current milliseconds since Epoch
    """
    return int(round(time.time() * 1000))


#    Convert the UNIX time in ms into ISO format
def to_iso(unixtime):
    """ The function converts the UNIX time to ISO format
    :param unixtime: UNIX time expressed in milliseconds
    :return: the time in ISO format
    """
    isodate = datetime.utcfromtimestamp(float(unixtime/1000)).isoformat()
    return isodate


#    Convert the UNIX time in ms into ISO format
def to_unix(isodate):
    """ The function converts the ISO timestamp into UNIX timestamp
    :param isodate: timestamp in ISO format with T after date and Z after time
    :return: the time in UNIX format
    """
    unixtime = calendar.timegm(datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
    unixtime *= 1000
    return unixtime


def validate_isodate(isodate):
    """ The function check if a date is
    :param isodate: timestamp in a format to check if the date is in ISO format
    :return: Boolean, False if the date is invalid
    """
    try:
        datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        pass
        print("Incorrect data format, should be YYYY-mm-ddTHH:MM:SS.Z")
        return False
    return True


#   Reset the STARTTIME global variable to 0
def reset_starttime():
    """ The function set to 0 the global variable STARTING_TIMESTAMP
    :return: None
    """
    global STARTING_TIMESTAMP
    STARTING_TIMESTAMP = 0


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
    parser.add_argument('--token', type=str, required=True, default="", help="Token in relayr Dashboard")
    parser.add_argument('--device', type=str, required=True, default=0, help="Device")
    parser.add_argument('--norm', type=int, required=False, default=1, help="Normalization value to divide the reading")
    parser.add_argument('--timestamp', type=int, required=False, default=0, help="Starting Timestamp")
    parser.add_argument('--timestampISO', type=str, required=False, default=0, help="Starting Timestamp in ISO format")
    return parser.parse_args()


#######################################################################################################################
#   Calling Main Function                                                                                             #
#######################################################################################################################

if __name__ == '__main__':
    #   Assign passed parameters to global variables
    args = parse_args()
    TOKEN = args.token
    DEVICE_ID = args.device
    DB_NAME = args.db
    FREQ_CHECKING = args.freq
    HOST = args.host
    PORT = args.port
    NORM = args.norm
    if STARTING_TIMESTAMP != 0:
        STARTING_TIMESTAMP = args.timestamp
    else:
        STARTING_TIMESTAMP = args.timestampISO
    if len(STARTING_TIMESTAMP) > 11:
        if not validate_isodate(STARTING_TIMESTAMP):
            exit()
    main()
