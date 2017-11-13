# Raw Data Downloader

## Introduction
<!--A brief description of the purpose and functionality of the project.-->
The Raw Data Downloader is a Python 3 script that downloads the raw data of a given device registered in the relayr Cloud 2.0 and afterwards it stores it into an InfluxDB instance.

You can use this script to have always a 1:1 local copy of the raw data from the cloud.

## Requirements
<!--A list of all system requirements and required third-party components.-->
For the correct use of this script, you must have:

- credentials for relayr Cloud 2.0;
- [Python 3.X](https://www.python.org/downloads/) with [PIP](https://pip.pypa.io/en/stable/installing/);
- [InfluxDB](https://docs.influxdata.com/influxdb/v1.3/) installed on your device.

## Installation & Configuration
<!--Step-by-step instructions, with proper punctuation, on how to install and configure the project.-->
### 1) Install the InfluxDB Client for Python
As written in the official [InfluxDB repository](https://github.com/influxdata/influxdb-python) you can use PIP to install the InfluxDB client:

```# pip install influxdb```

or update if you have already installed it:

```# pip install --upgrade influxdb```

**NOTE**: if you are using MacOS El Capitan or a more recent version and you are not using a virtualenv, please instead use this command:
	
```# pip install influxdb --ignore-installed six```
	
If you use a Debian/Ubuntu based distribution, you can install via the APT package manager:

```$ sudo apt-get install python-influxdb```
	
### 2) Install the Requests module for Python
For install the [Requests](http://docs.python-requests.org/en/master/) module for Python:

```# pip install requests```

or update if you have already installed it:

```# pip install --upgrade requests```


### 3) Run the script
For running the script you have just to browse with your terminal into the folder where you have the script and launch the command, for example:

```$ sudo python3 /path_to/raw-data-downloader.py --device myDEVICE_ID --db myDB --org myORG --password myPASS --user myUSER```
	
Output example:

```	
Connecting to InfluxDB...
Connection to InfluxDB established
Acquiring a new refresh token
Refresh token saved
Requesting a new access token...
New access token saved
Measurements to download:
temperature
humidity
Started download thread for the measurement: temperature
Started download thread for the measurement: humidity
2017-11-13T10:58:51.287Z - humidity - 30
2017-11-13T10:58:56.556Z - humidity - 30
2017-11-13T10:58:51.287Z - temperature - 23
2017-11-13T10:58:56.556Z - temperature - 23
``` 
	
#### Parameters
	
| Parameter |  Type  | Required | Default |                     Example                    |
|:---------:|:------:|:--------:|:-------:|:----------------------------------------------:|
| --db  	  | string |    yes   |         | --db my_DBname                                 |
| --device  | string |    yes   |         | --device 1112a222-3333-4455-6666-777f7f7f7fff7 |
| --user    | string |    yes   |         | --user my_USER                                 |
| --password | string |  yes    |         | --password my_USERpassword                     |
| --org     | string |   yes    |         | --org my_ORG                                   |
| --start   | string |    no    | local time - 1h | --start 2017-11-13T10:30:15Z           |
| --influxdb_address | string | no | localhost | --influxdb_address 192.168.0.4            |
| --influxdb_port | int | no    | 8086    | --influxdb_port 8090                           |
| --special_char | string | no  | None    | --special_char _                               |
| --refresh | int	|    no     | 10		  | --refresh 10                                   |

**db:** the name of the local InfluxDB database where you want to save your readings;

**device:** the deviceID of the device on relayr Cloud 2.0;

**user:** the user ID in relayr Cloud 2.0;

**password:** the user password in relayr Cloud 2.0;

**org:**  the organization in relayr Cloud 2.0;

**start:**  the starting time from when download data from the cloud, in ISO time format;

**influxdb_address:** the host of the InfluxDB instance;

**influxdb_ port:** the port of the InfluxDB instance;

**special_char:** if it is not `None`, only the measurements name containing this character will be downloaded;

**refresh:** the frequency of checking the cloud if there are new readings available, in seconds.

#### Notes

The script creates a table inside a database for each meaning of your device.
Note that the script creates also a file called `YOUR_DB_NAME.db`. It is a Berkeley DB created through the shelve module of Python. It should be found in the folder where you run the script and it cointains the timestamp of the last reading received.

## License
<!--The license under which the software will be released. Open-source projects MUST include the MIT License, and closed-source projects MUST include a proprietary license to be discussed with the Documentation team.
-->
The MIT License (MIT)
Copyright (c) 2017 relayr Inc., Riccardo Marconcini [riccardo DOT marconcini AT relayr DOT de](mailto:riccardo.marconcini@relayr.de)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.