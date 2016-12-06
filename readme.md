# History Downloader from relayr to InfluxDB

## Introduction
<!--A brief description of the purpose and functionality of the project.-->
The History Downloader is a script written in Python that downloads the readings of a given device registered in the relayr cloud and store them into your local instance of InfluxDB.

## Requirements
<!--A list of all system requirements and required third-party components.
-->
For the correct use of this script, you must have:

- a registered device in the relayr dashboard;
- Python 3.X installed on your device with PIP;
- InfluxDB installed on your device. 

## Installation & Configuration
<!--Step-by-step instructions, with proper punctuation, on how to install and configure the project.-->
### 1) Install the InfluxDB Client for Python
As written in the official [InfluxDB repository](https://github.com/influxdata/influxdb-python) you can use PIP to install

	# pip install influxdb

or update if you have already installed it.

	# pip install --upgrade influxdb
	
If you use Debian/Ubuntu based distribution, you can install via the APT package manager:

	$ sudo apt-get install python-influxdb

### 2) Install the relayr SDK for Python
You can install with PIP the last version directly from GitHub:

	# pip install git+https://github.com/relayr/python-sdk

### 3) Run the script
For running you just have to browse with your terminal into the folder where you have the script and launch the command, for example:

	$ python3 history_downloader.py --token 1234567890 --device 0987654321 --db DBname
	
#### Parameters
	
| Parameter |  Type  | Required | Default |                     Example                    |
|:---------:|:------:|:--------:|:-------:|:----------------------------------------------:|
|  --token  | string |    yes   |         |       --token P7hTR4rgf5P670q5MzYkNogs8K       |
|  --device | string |    yes   |         | --device 1112a222-3333-4455-6666-777f7f7f7fff7 |
|    --db   | string |    yes   |         |                   --db dbname                  |
|    --freq   | int |    no   |    60     |                   --freq 3000                  |
|    --host   | string |    no   |     localhost    |                   --host 127.1.4.3                  |
|    --port   | int |    no   |    8086     |                   --port 4000                  |
|    --norm   | int |    no   |     1    |                   --norm 100                  |

**token:** the account token you can find in your account page in relayr
dashboard;

**device:** the device ID;

**db:** the name of the database where you want to save your readings;

**freq:** the frequency of checking the cloud if there are new readings available;

**host:** the host of your local InfluxDB instance;

**port:** the port of your local InfluxDB instance;

**norm:** if the readings on the cloud need to be normalized, this is the factor to divide the readings.

#### Notes

The script creates a table inside a database for each meaning of your device.
Note that the script creates a file called `history_downloader_settings.db`. It is a Berkeley DB creadted through the shelve module of Python. It should be created in the folder where you run the script and it cointains the timestamp of the last reading received.

## License
<!--The license under which the software will be released. Open-source projects MUST include the MIT License, and closed-source projects MUST include a proprietary license to be discussed with the Documentation team.
-->
The MIT License (MIT)
Copyright (c) 2016 relayr Inc., Riccardo Marconcini [riccardo DOT marconcini AT relayr DOT de](mailto:riccardo.marconcini@relayr.de)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.