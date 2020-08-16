# FAA DB
A quick-and-dirty REST API for looking up FAA aircraft registration information. This tool is designed to be operated as a stand-alone project with no Internet connection between ETL runs. An internet connection is required to download the database initially or update it later. As of this writing the FAA database zip file is updated daily at 23:30 Central time.

## Background
This software is a Python application backed by MongoDB which can be used to query the publicly available FAA aircraft database given a US aircraft tail number, and ICAO aicraft address in either hexidecimal or integer format using a basic RESTful API. This application also has a built-in ETL process which can be called from the API to do an initial data load or refresh from the FAA aircraft registration database. This is the only process which requires an Intenet connection. It should be noted that the ETL does not load data about aircraft that have been deregistered. The FAA provides this dataset publicly and for free.

## Prerequisites, Set-up, and basic operations
### Prerequisites
* Linux or Mac computer or VM. This has not been tested on Windows.
* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* Internet connection for initial data load and any subsequent runs of the ETL process.

### Core technologies
* Docker - Containerization tool chain
* Docker Compose - Provides local container orchestration
* Python 3.7.8 - Python version the code was written in
* Flask - Python-based web server package
* MongoDB - Database engine
* Pandas - Open source data manipulation and analysis tool
* Pipenv - Dependency management and Python environment for local development
* Pyenv - Python version manager for development

### Initial installation and set up
* Ensure the prerequisites have been met.
* Clone this [repo](https://github.com/ThreeSixes/faaDb.git).
* `cd` into this repo and run `docker-compose up --build` The application will restart by default along with the Docker daemon.
* After both containers build and start the web service should be listening for API requests on port `8080`.
* You can use CURL to call the API and trigger the ETL process. This will take a few minutes to finish as there are about 250,000 registered aircraft at the time of this writing. Example CURL command: `curl -i http://127.0.0.1:8080/api/v1.0/faa-database`

### Updating
In order to update the application itself use the following steps:
* cd in to the repo's directory.
* If the application is running issue a `docker-compose down`
* Run `git pull`
* Run `docker-compose up --build`
  
### Starting and stopping
In order to start or stop the application run one of the following after `cd`int into the repo:
* Starting: `docker-compse up`
* Stopping: `docker-compse down`

## Using the API
The API is RESTful and exposes a limited number of endpoints. You can request aircraft information using the tail number beginning with N, or the ICAO aircraft address as a 6-digit hex string or integer. Each of these have their own API endpoint. Data refreshes and loads are also triggered by API endpoints. The aircraft information is returned as a JSON body. Malformed or invalid data will return either an 400 or 404 with a JSON formatted message.

### API endpoints for retrieving aircraft information
* `/api/v1.0/tail-number/[US tail number]` - Returns a JSON blob describing any matching aircraft. If the tail number is not found in the database a 404 is returned. The tail number is canse insensitive. Supported methods: `GET`
* `/api/v1.0/icao-hex/[abc012]` - Returns a JSON blob describing any matching aircraft. If the hexidecimal ICAO address is not found in the database a 404 is returned. The ICAO address is canse insensitive. Supported methods: `GET`
* `/api/v1.0/icao-hex/[integer]` - Returns a JSON blob describing any matching aircraft. If the integer ICAO address is not found in the database a 404 is returned. Supported methods: `GET`

### API endpoints for the ETL process
* `/api/v1.0/faa-database` - Trigger the full ETL process as described in the theory of operation section. This operation takes a few minutes to run. Supported methods: `GET`
* `/api/v1.0/faa-database-download` - Trigger the download of the FAA aicraft database zip file. This is mostly for debugging. Supported methods: `GET`
* `/api/v1.0/faa-database-etl` - Trigger the extraction of data from a previously-downloaded ziop file. This is mostly for debugging. Supported methods: `GET`

## Theory of operation
### ETL
The ETL (Extract, Transform, Load) process executes the following steps:
* The FAA aicraft database zip file is downloaded. See the `Additional Resources` section.
* The zip file is extracted.
* The `MASTER.txt`, `ENGINE.txt`, and `ACFTREF.txt` files are loaded by `Pandas`.
* The columns are manipulated to be suitable for merging and storage.
* Engine and aicraft reference data are merged to the master data.
* The resultant dataset is then loaded into a MongoDB staging collection.
* Once the data has fully been loaded into the staging collection we check for an existing live collection. If it exists its deleted.
* The staging collection is then renamed to be the live collection and is ready for queries.

### REST API
The REST API leverages Flask to search the MongoDB for records on specific keys after validating the search parameters and retuns a JSON blob with either the aicraft information or a message about the status of the request. Successful requests for information result in HTTP `200` status codes. If the search terms or request are invalid a `400` is returned. In the event there is an invalid API endpoint or no data returned a `404` is returned. Unhandled exceptions result in HTTP `500`s.

All requests are normalizd so they can be case insensitive. Both tail numbers and ICAO hex addresses are case insesitive.

## Query exmaples using CURL and jq
Given an aircraft tail number of `N287AK`, ICAO hex address (`A2E806`) or integer address (`50564006`) we can look up aircraft information. These examples use `jq` to make the data more human-friendly.
Query by tail number:

`curl http://127.0.0.1:8080/api/v1.0/tail-number/N287AK | jq .`

This query results in:

```json
[
  {
    "acft_ac-cat": 1,
    "acft_ac-weight": "CLASS 3",
    "acft_build-cert-ind": 0,
    "acft_code": "138488H",
    "acft_mfr": "BOEING",
    "acft_model": "737-900ER",
    "acft_no-eng": 2,
    "acft_no-seats": 222,
    "acft_speed": 0,
    "acft_type-acft": "5",
    "acft_type-eng": 5,
    "air-worth-date": "Wed, 09 May 2018 00:00:00 GMT",
    "cert-issue-date": "Tue, 15 May 2018 00:00:00 GMT",
    "certification": "1T",
    "city": "SEATAC",
    "country": "US",
    "county": "033",
    "eng_horsepower": 0,
    "eng_mfr": "CFM INTL",
    "eng_model": "CFM56-7B27E",
    "eng_thrust": 27300,
    "eng_type": "5",
    "expiration-date": "Mon, 31 May 2021 00:00:00 GMT",
    "fract-owner": null,
    "kit-mfr": null,
    "kit-model": null,
    "last-action-date": "Thu, 01 Jan 1970 00:00:00 GMT",
    "mode-s-code": 50564006,
    "mode-s-code-hex": "A2E806",
    "n-number": "N287AK",
    "name": "ALASKA AIRLINES INC",
    "other-names-1": null,
    "other-names-2": null,
    "other-names-3": null,
    "other-names-4": null,
    "other-names-5": null,
    "region": "S",
    "serial-number": "36359",
    "state": "WA",
    "status-code": "V",
    "street": "C/O LEGAL DEPT SEA2L",
    "street2": "19300 INTERNATIONAL BLVD",
    "type-aircraft": "5",
    "type-engine": 5,
    "type-registrant": "3",
    "unique-id": 1272641,
    "year-mfr": "2018",
    "zip-code": "981885304"
  }
]
```

`GET` requests for this aircraft's ICAO addrsses will also result in the same JSON body being returned:
* `curl http://127.0.0.1:8080/api/v1.0/icao-int/50564006`
* `curl http://127.0.0.1:8080/api/v1.0/icao-hex/A2E806`

## Known issues and limitations
* This code is an MVP for quickly querying data. It's not production grade.
* There is no web or CLI client for the API. If anyone wants to create one I'd be eternally greatful.
* The FAA database only contains information about US aircraft.
* This application does not import deregistered aircraft.
* The web service is HTTP only.
* If the MongoDB container is destroyed the FAA database contained in it is lost and will have to be reloaded via the ETL next time it's created.
* The ETL does not run automaically, but a Cron job that runs daily at an apporprate time should resolve the issue.

## Additional resources
Data dictionary for fields from the FAA website: [https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/media/ardata.pdf](https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/media/ardata.pdf)

FAA database download page: [http://registry.faa.gov/database/ReleasableAircraft.zip](http://registry.faa.gov/database/ReleasableAircraft.zip)

### License
This software is licensed under GPLv3. A copy of the license is provided in the `LICENSE` file in this repository.