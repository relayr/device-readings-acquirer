#######################################################################################################################
#   Libraries, Modules & API                                                                                          #
#######################################################################################################################
import shelve
import requests
import time
import argparse
import threading
import datetime
from influxdb import InfluxDBClient


#######################################################################################################################
#   Global Variables                                                                                                  #
#######################################################################################################################

USER = ''
PASSWORD = ''
ORG = ''
START = ''
GROUP = ''
INFLUXDB_ADDRESS = ''
INFLUXDB_PORT = 0
DB = ''
REFRESH_TOKEN = ''
TOKEN = ''
SPECIAL_CHAR = ''
REFRESH = 0


#######################################################################################################################
#   Main                                                                                                              #
#######################################################################################################################
def main():

    global REFRESH_TOKEN

    # Cycle until it is established the connection to the local instance of InfluxDB.
    while True:
        try:
            print('Connecting to InfluxDB...')
            influxClient = InfluxDBClient(INFLUXDB_ADDRESS, INFLUXDB_PORT, "root", "root")

            # If the database already exists, the creation is skipped.
            influxClient.create_database(DB)

            print("Connection to InfluxDB established")
            break
        except:
            print("InfluxDB not ready: retrying...")
            time.sleep(5)

    # Request a refresh token.
    print("Acquiring a new refresh token")
    refresh_token_req = requests.post('https://login.relayr.io/oauth/token?client_id=api-client',
                                      data={'username': USER, 'password': PASSWORD, 'org': ORG})

    # Parse the JSON received as answer.
    refresh_token_req_json = refresh_token_req.json()

    print("Refresh token saved")
    # Save the access_token and the refresh_token.
    REFRESH_TOKEN = refresh_token_req_json['refreshToken']
    TOKEN = refresh_token_req_json['accessToken']

    # Create an instance of TokenClass and start it.
    tokenclass = TokenClass()
    tokenclass.start()

    # Request the group info.
    group_req = requests.get('https://cloud.relayr.io/device-groups/'+GROUP+'/flat',
                             headers={'authorization': 'Bearer '+TOKEN})

    # Parse the JSON received as answer.
    group_req_json = group_req.json()

    device_list = []

    # Extract the devices IDs from the JSON.
    for dic in group_req_json['devices']:
        device_list.append(dic['id'])

    raw_class_list = []

    # Loop for every device of the group.
    for device in device_list:

        # Request the device info.
        device_req = requests.get('https://cloud.relayr.io/devices/'+device,
                                  headers={'authorization': 'Bearer '+TOKEN})

        # Parse the JSON received as answer.
        device_req_json = device_req.json()

        # Save the modelId and and modelVersion.
        modelId = device_req_json['modelId']
        modelVersion = str(device_req_json['modelVersion'])

        print('Downloading data for device ' + device_req_json['name'] + ' (' + device_req_json['id'] + ')')

        # Requrst the model info.
        model_req = requests.get('https://cloud.relayr.io/device-models/'+modelId+'/versions/'+modelVersion,
                                 headers={'authorization': 'Bearer '+TOKEN})

        # Parse the JSON received as answer.
        model_req_json = model_req.json()

        measurements_names = []

        # Cycle all the measurements.
        for i in range(len(model_req_json['measurements'])):

            # If there is the special character.
            if SPECIAL_CHAR is not None:

                # Append to measurements_name only the measurements containing the special char.
                for char in model_req_json['measurements'][i]['name']:
                    if char == SPECIAL_CHAR:
                        measurements_names.append(model_req_json['measurements'][i]['name'])
                    pass

            # Otherwise append all the measurements.
            else:
                measurements_names.append(model_req_json['measurements'][i]['name'])

        print('Measurements to download:')
        for i in range(len(measurements_names)):
            print(measurements_names[i])

        # Start a thread for every different measurement.
        for i in range(len(measurements_names)):

            # Create a thread passing the influx client and the name of the measurement to download.
            thread_tmp = RawClass(influxClient, device, device_req_json['name'], measurements_names[i])

            # Append the thread to the measurements thread list.
            raw_class_list.append(thread_tmp)

            # Start the thread.
            thread_tmp.start()


#######################################################################################################################
#   Functions                                                                                                         #
#######################################################################################################################

def validate_isodate(isodate):
    """ The function check if a string is a date in ISO time format
    :param isodate: timestamp in a format to check if the date is in ISO format
    :return: Boolean, False if the date is not in ISO format
    """
    try:
        datetime.datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%SZ")
        print('Date parameter is in a valid ISO format.')
    except ValueError:
        pass
        print('Incorrect data format, should be YYYY-mm-ddTHH:MM:SSZ')
        return False
    return True


#######################################################################################################################
#   Classes                                                                                                           #
#######################################################################################################################

class TokenClass(threading.Thread):
    """ The class extends the Thread class. When it runs, it requests a new access token with the refresh token and
        then sleeps until a minute before the expiration of token to run again.
    """
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global TOKEN

        while True:

            print('Requesting a new access token...')
            # Request a new token using the refresh token.
            new_token_request = requests.post('https://login.relayr.io/oauth/refresh?client_id=api-client',
                                              headers={'Content-Type': 'application/json'},
                                              json={'refresh_token': REFRESH_TOKEN})

            # Parse the JSON received as answer.
            new_token_request_json = new_token_request.json()

            # Save the access token.
            TOKEN = new_token_request_json['accessToken']
            print('New access token saved')

            # Sleep the thread until a minute before the expiration.
            time.sleep(new_token_request_json['expiresIn']-60)


class RawClass(threading.Thread):
    """ The class downloads the measurements and saves them in influxdb, then sleeps and start again from the last
        timestamp.
    """
    def __init__(self, influxClient, device, devname, measurement_name):
        threading.Thread.__init__(self)
        self.name = measurement_name
        self.influxClient = influxClient
        self.device = device
        self.devname = devname

    def run(self):

        print('Started download thread for the measurement: '+self.name)
        global TOKEN

        # The first time the thread runs it should use the start timestamp provided via command line if it is present.
        # Using a flag to avoid to overwrite with stored timestamp during first start.
        flag = False
        last_timestamp = START

        while True:

            # Use as last timestamp the passed parameter if flag is false (only first run)
            if flag:
                last_timestamp = self.get_last_timestamp()

            # Request the raw measurements providing the last timestamp, the device id and measurements name.
            raw_req = requests.get('https://cloud.relayr.io/devices/' + self.device +
                                   '/raw-measurements?measurements=' + self.name +
                                   '&start=' + last_timestamp,
                                   headers={'authorization': 'Bearer ' + TOKEN})

            # Parse the received JSON.
            raw_req_json = raw_req.json()

            print(raw_req.text)

            data = []

            # If new data are received.
            if len(raw_req_json) != 0:

                # Cycle all the measurements and append name, timestamp and value in data.
                for j in range(len(raw_req_json)):
                    data.append({
                        'measurement': raw_req_json[j]['name'],
                        'time': raw_req_json[j]['timestamp'],
                        'fields': {'value': float(raw_req_json[j]['value'])}
                    })

                    # Update the last timestamp every time the cycle has measurements.
                    last_timestamp = raw_req_json[j]['timestamp']

                    print(raw_req_json[j]['timestamp'] + ' - ' + self.devname + ' - ' + raw_req_json[j]['name'] + ' - '
                          + str(raw_req_json[j]['value']))

                try:
                    # Save data in influxDB.
                    self.influxClient.write_points(data, database=DB, time_precision="ms")
                except:
                    print("Error writing into influxDB")
                    print(data)

                # Convert the las timestamp in a datetime object.
                tmp_timestamp = datetime.datetime.strptime(last_timestamp,'%Y-%m-%dT%H:%M:%S.%fZ')

                # Increase the timestamp of 1ms to avoid to download again next time the last measurement.
                increased_timestamp = str(tmp_timestamp + datetime.timedelta(milliseconds=1))

                # Save the last timestamp with shelves.
                self.set_last_timestamp(str(increased_timestamp))

                # Set flag true to use last timestamp for next cycle.
                flag = True

            # Sleep the thread for the refresh period.
            time.sleep(REFRESH)

    # Set function for the last timestamp using the shelf module
    def set_last_timestamp(self, timestamp):
        """ The function saves the timestamp through the shelve module
        :param timestamp: str
        :return: None
        """

        # Open the shelve object.
        s = shelve.open(str(DB))
        try:
            # Save the timestamp as value, the key is the name of the measurement.
            s[self.name] = timestamp
        except:
            print("Impossible access to the settings file. Error with timestamp set.")
        finally:
            s.close()

    # Get function for the last timestamp using the shelf module
    def get_last_timestamp(self):
        """ The function gets the timestamp through the shelve module
        :return: str
        """

        # Open the shelve object.
        s = shelve.open(str(DB))
        try:
            # Get the value using as key the name of the measurements.
            existing = s[self.name]
        except:
            print("Impossible access to the settings file. Error with timestamp get.")
        finally:
            s.close()
        return existing


#######################################################################################################################
#   Parsing Command Line Args                                                                                         #
#######################################################################################################################
def parse_args():
    """ The function parse the args specified in the CLI.
    :return: parsed args
    """
    parser = argparse.ArgumentParser(description="MQTT to InfluxDB")
    parser.add_argument('--db', type=str, required=True,
                        help="Name of InfluxDB database where save the data.")
    parser.add_argument('--group', type=str, required=True,
                        help="The ID of the group to download the measurements.")
    parser.add_argument('--user', type=str, required=True,
                        help="The user in relayr cloud.")
    parser.add_argument('--password', type=str, required=True,
                        help="The password in relayr cloud.")
    parser.add_argument('--org', type=str, required=True,
                        help="The organization in relayr cloud.")
    parser.add_argument('--start', type=str, required=False, default=None,
                        help="The starting time from when download data.")
    parser.add_argument('--influxdb_address', type=str, required=False, default="localhost",
                        help="The address where is hosted the local instance of InfluxDB.")
    parser.add_argument('--influxdb_port', type=int, required=False, default=8086,
                        help="The port where is running the local instance of InfluxDB.")
    parser.add_argument('--special_char', type=str, required=False, default=None,
                        help="The char in measurement name used to filter the selection.")
    parser.add_argument('--refresh', type=int, required=False, default=10,
                        help="Seconds to wait before downloading again new raw data.")
    return parser.parse_args()


#######################################################################################################################
#   If main statement                                                                                                 #
#######################################################################################################################
if __name__ == '__main__':

    # Assign passed parameters to global variables.
    args = parse_args()
    DB = args.db
    GROUP = args.group
    USER = args.user
    PASSWORD = args.password
    ORG = args.org
    START = args.start
    INFLUXDB_ADDRESS = args.influxdb_address
    INFLUXDB_PORT = args.influxdb_port
    SPECIAL_CHAR = args.special_char
    REFRESH = args.refresh

    # Control if the passed starting date is in the requested format.
    if START is not None:

        # If the date passed is not valid, setting up the default start: one hour before the script starting.
        if not validate_isodate(START):
            START = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    else:
        START = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

    main()
