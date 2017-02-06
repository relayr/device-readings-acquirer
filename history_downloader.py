"""
Relayr to InfluxDB History Downloader v2.2.2

This script is a bridge between the Relayr cloud and a local instance of InfluxDB.
It downloads the data of a certain device and store them in local.

Last Edit: 06 Feb 2017 12.37 CET

Copyright Riccardo Marconcini (riccardo DOT marconcini AT relayr DOT de)

TODO: add how many rows are added for each meaning
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
PORT = 0
NORM = 1
STARTING_TIMESTAMP = 0
APP_ID = ""
EXPIRY_DATE = 0


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

        #   Control of the last timestamp or the given one if parsed from command line
        try:
            if STARTING_TIMESTAMP != 0:
                if isinstance(STARTING_TIMESTAMP, int):
                    last_timestamp = STARTING_TIMESTAMP
                else:
                    last_timestamp = to_unix(STARTING_TIMESTAMP)
            else:
                last_timestamp = get_last_timestamp()
        except:
            print("Last timestamp not found. Setting as default three days ago...")
            last_timestamp = (current_milli_time() - 259200000)
        print("Last Timestamp: ", last_timestamp, to_iso(last_timestamp))

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

                #   Get the model ID from the device ID
                device_info = requests.get('https://api.relayr.io/devices/' + DEVICE_ID,
                                           headers={'authorization': 'Bearer ' + TOKEN,
                                                    "cache-control": "no-cache"})
                device_info_json = device_info.json()

                #   Request the model ID to retrieve the meanings
                model_info = requests.get('https://api.relayr.io/device-models/' + device_info_json['modelId'],
                                          headers={"authorization": "Bearer " + TOKEN,
                                                   "cache-control": "no-cache"})
                model_info_json = model_info.json()

                meanings = []
                for i in range(len(model_info_json['firmware']['1.0.0']['transport']['cloud']['readings'])):
                    meanings.append(model_info_json['firmware']['1.0.0']['transport']['cloud']
                                    ['readings'][i]['meaning'])

                #   For every meaning the script performs a request and parse the readings into the
                #   data var
                for i in range(len(meanings)):
                    readings = requests.get('https://api.relayr.io/devices/' + DEVICE_ID
                                            + '/aggregated-readings?meaning=' + meanings[i]
                                            + '&start=' + to_iso(last_timestamp)
                                            + '&interval=10s&aggregates=avg',
                                            headers={"authorization": "Bearer " + TOKEN,
                                                     "accepted": "application/json"})
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
            print("Error writing into influxDB")

        #   Reset the START_TIME, if the script is launched with --timestamp, it is used only for the first iteration
        reset_starttime()

        #   If a token will expire up to 30 minutes after the next iteration, a new token will be generated
        if current_milli_time() + (FREQ_CHECKING * 1000) + 1800000 > EXPIRY_DATE:
            request_new_token(TOKEN, APP_ID)
            assign_token(get_token())
            assign_expiry_date(get_expiry_date())

        #   Sleep
        print("Sleeping for the next ", FREQ_CHECKING, " seconds... \n")
        time.sleep(FREQ_CHECKING)


#######################################################################################################################
#   Functions                                                                                                         #
#######################################################################################################################

#   Set function for the last timestamp using the shelf module
def set_last_timestamp(timestamp):
    """ The function saves the timestamp through the shelve module
    :param timestamp: int
    :return: None
    """
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        s['last_timestamp'] = timestamp
    except:
        print("Impossible access to the settings file. Error with timestamp set.")
    finally:
        s.close()


#   Get function for the last timestamp using the shelf module
def get_last_timestamp():
    """ The function gets the timestamp through the shelve module
    :return: int
    """
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        existing = s['last_timestamp']
    except:
        print("Impossible access to the settings file. Error with timestamp get.")
    finally:
        s.close()
    return existing


#   Request new token function
def request_new_token(old_token, app_id):
    """ The function requests a new token given an existing token and the app ID
    :param old_token: string
    :param app_id: string
    :return: None
    """
    try:
        new_token_request = requests.post("https://api.relayr.io/oauth2/appdev-token/" + app_id,
                                          headers={"authorization": "Bearer " + old_token,
                                                   "cache-control": "no-cache"})
        new_token_json = new_token_request.json()
        set_token(new_token_json['token'], new_token_json['expiryDate'])
    except:
        print("Error with new token request.")


#   Set function for the token using the shelf module
def set_token(token, expiry_date):
    """ The function gets the timestamp through the shelve module
    :param token: string
    :param expiry_date: int
    :return: None
    """
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        s['token'] = token
        s['expiry_date'] = expiry_date
    except:
        print("Impossible to access settings file. Error with token set.")
    finally:
        s.close()


#   Get function for the token using the shelf module
def get_token():
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        token = s['token']
    except:
        print("Impossible to access settings file. Error with token get.")
    finally:
        s.close()
    return token


#   Get function for the token using the shelf module
def get_expiry_date():
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        expiry_date = s['expiry_date']
    except:
        print("Impossible to access settings file. Error with expiry date get.")
    finally:
        s.close()
    return expiry_date


#   Get function for the last appID using the shelf module
def check_appID():
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        found = 'appID' in s
    except:
        print("Impossible to create settings file. Error with token set.")
    finally:
        s.close()
    return found


#   Set the appID using the shelve module
def set_appID(appID):
    """ The function return the appID from the shelf module
    :return: None
    """
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        s['appID'] = appID
    except:
        print("Impossible to create settings file. Error with appID set.")
    finally:
        s.close()


#   Get the appID from the shelve module
def get_appID():
    """ The function return the appID from the shelf module
    :return: string
    """
    s = shelve.open('history_downloader_settings_' + DB_NAME)
    try:
        app_ID = s['appID']
    except:
        print("Impossible to create settings file. Error with appID get.")
    finally:
        s.close()
    return app_ID


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
    """ The function check if a string is a date in ISO time format
    :param isodate: timestamp in a format to check if the date is in ISO format
    :return: Boolean, False if the date is not in ISO format
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


#   Assign the token to the global variable
def assign_token(token):
    """ The function set a new token to the corresponding global variable
    :return: None
    """
    global TOKEN
    TOKEN = token


#   Assign the expiry date to global variable
def assign_expiry_date(expiry_date):
    """ The function set a new expiry date to the corresponding global variable
    :return: None
    """
    global EXPIRY_DATE
    EXPIRY_DATE = expiry_date


#######################################################################################################################
#   Parsing Command Line Args                                                                                         #
#######################################################################################################################

def parse_args():
    """ The function parse the args specified in the CLI.
    :return: parsed args
    """
    parser = argparse.ArgumentParser(description="History Downloader from relayr cloud to InfluxDB")
    parser.add_argument('--token', type=str, required=True, help="Authorization token in relayr Dashboard")
    parser.add_argument('--device', type=str, required=True, help="Device ID in relayr Dashboard")
    parser.add_argument('--db', type=str, required=True,
                        help="Name of the local influxDB database where to save the data")
    parser.add_argument('--freq', type=int, required=False, default=60,
                        help="How often check the cloud for new readings, expressed in seconds")
    parser.add_argument('--host', type=str, required=False, default="localhost",
                        help="Address where is hosted the local instance of InfluxDB")
    parser.add_argument('--port', type=int, required=False, default=8086,
                        help="Port where is running the local instance of InfluxDB")
    parser.add_argument('--norm', type=int, required=False, default=1,
                        help="Normalization factor to apply to the readings from the cloud")
    parser.add_argument('--timestamp', type=int, required=False, default=0, help="Starting Timestamp in UNIX format")
    parser.add_argument('--timestampISO', type=str, required=False, default="", help="Starting Timestamp in ISO format")
    return parser.parse_args()


#######################################################################################################################
#   If main statement                                                                                                 #
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

    #   Assign the timestamp parameter to global variable
    if args.timestamp != 0:
        STARTING_TIMESTAMP = args.timestamp
    elif args.timestampISO != "":
        if not validate_isodate(args.timestampISO):
            exit()
        else:
            STARTING_TIMESTAMP = args.timestampISO
    if args.timestamp == 0 and args.timestampISO == 0:
        STARTING_TIMESTAMP == 0

    #   If there is not an App registered on the cloud, the script creates a new app for being able to
    #   create a new token
    if not check_appID():

        #   Get the owner ID given the device ID
        device_req = requests.get('https://api.relayr.io/devices/' + DEVICE_ID,
                                  headers={"authorization": "Bearer " + TOKEN,
                                           "cache-control": "no-cache"})
        device_json = device_req.json()

        #   Get the publisher ID associated to a give user
        publishers_request = requests.get('https://api.relayr.io/users/' + device_json['owner'] + "/publishers",
                                          headers={"authorization": "Bearer " + TOKEN,
                                                   "cache-control": "no-cache",
                                                   "Content-Type": "application/json"})
        publishers_json = publishers_request.json()

        #   Get the list of app associated to a given publisher
        app_list_request = requests.get('https://api.relayr.io/publishers/' + publishers_json[0]['id'] + "/apps",
                                        headers={"authorization": "Bearer " + TOKEN,
                                                 "cache-control": "no-cache"})
        app_list_json = app_list_request.json()

        #   If there is already an existing app for this user, I save its id
        if len(app_list_json) > 0:
            APP_ID = app_list_json[0]['id']

        #   Otherwise a new stub app is created for generating the token
        else:

            app_request = requests.post("https://api.relayr.io/apps",
                                        headers={"authorization": "Bearer " + TOKEN,
                                                 "cache-control": "no-cache",
                                                 "Content-Type": "application/json"},
                                        json={"name": "POST app",
                                              "publisher": publishers_json[0]['id'],
                                              "redirectUri": "http://relayr.io",
                                              "description": "App to retrieve a token for History Downloader"})
            app_request_json = app_request.json()
            APP_ID = app_request_json['id']

        #   Save the App ID
        set_appID(APP_ID)
    else:

        #   Get the App ID
        APP_ID = get_appID()

    #   Request a new token before starting the main, so it is possible to know the expiry date
    request_new_token(TOKEN, APP_ID)

    #   Assign the token and the expiry date to the global variables
    TOKEN = get_token()
    EXPIRY_DATE = get_expiry_date()

    main()
