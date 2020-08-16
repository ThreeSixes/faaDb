import datetime
import os
import re

from customexceptions import InvalidSearchFormat, SearchResultNotFound
from etl import FaaDbETL
from flask import Flask, jsonify, abort
from mongo import FaaDbMongo


def print_log(string):
    """ Print string with timestamp. """

    now = datetime.datetime.utcnow()
    now_str = datetime.datetime.strftime(now, '%Y-%m-%dT%H:%M:%S.%f+0000')
    print("%s - %s" %(now_str, string))


print_log("Starting the FAA DB web service.")

# Load configuration
etl_clean_up = os.getenv('ETL_CLEANUP', "true")
flask_debug = os.getenv('FLASK_DEBUG', "false")
flask_host = os.getenv('FLASK_HOST', "127.0.0.1")
flask_port = int(os.getenv('FLASK_PORT', 5000))
mongo_db_name = os.getenv('MONGO_DB', "faa")
mongo_coll_name = os.getenv('MONGO_COLL', "aircraft-registered")
mongo_host = os.getenv('MONGO_HOST', "mongodb")
mongo_port = int(os.getenv('MONGO_PORT', 27017))

# Does the ETL process delete files?
if etl_clean_up.lower() == "true":
    etl_clean_up = True
else:
    etl_clean_up = False

# Do we start Flask in debug mode?
if flask_debug.lower() == "true":
    flask_debug = True
else:
    flask_debug = False

# Create oure pre-compiled regexes.
icao_aa_hx_regex = re.compile("^[A-Z0-9]{6}$")
icao_aa_int_regex = re.compile("^[0-9]+$")
us_tail_number_regex = re.compile("^N[0-9A-Z]+$")

# Create database and ETL objects.
db = FaaDbMongo(mongo_host, mongo_port, db_name=mongo_db_name, coll_name=mongo_coll_name)
etl = FaaDbETL(clean_up=etl_clean_up)

# Create our Flask app
app = Flask(__name__)

# Register error handlers.
@app.errorhandler(SearchResultNotFound)
def handle_search_result_not_found(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.errorhandler(InvalidSearchFormat)
def handle_invalid_search_format(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

# Search by tail number.
@app.route('/api/v1.0/tail-number/<tail_number>', methods=['GET'])
def search_by_tail_number(tail_number):
    records = []
    results = {}
    tail_number = tail_number.upper()

    if re.match(us_tail_number_regex, tail_number):
        results = db.search_tail_number(tail_number)

        for result in results:
            result.pop('_id')
            records.append(result)

        if len(records) < 1:
            raise SearchResultNotFound("The tail number was not found in the FAA database.")

        else:
            for result in results:
                result.pop('_id')
                records.append(result)

    else:
        raise InvalidSearchFormat("US Aircraft tail numbers begin with N and contain one or " \
            "of the following characters: 0-9, A-F. The tail number you provided did not.")

    return jsonify(records)

# Search by ICAO Aircraft Address in hex format.
@app.route('/api/v1.0/icao-hex/<icao_aa>', methods=['GET'])
def search_by_icao_aa_hx(icao_aa):
    icao_aa = icao_aa.upper()
    records = []
    results = {}

    if re.match(icao_aa_hx_regex, icao_aa):
        results = db.search_icao_aa_hx(icao_aa)

        for result in results:
            result.pop('_id')
            records.append(result)
 
        if len(result) < 1:
            raise SearchResultNotFound("The ICAO address was not found in the FAA database.")

    else:
        raise InvalidSearchFormat("Hexidecmial ICAO aircraft addresses are 6 characters in " \
            "length and only contain 0-9, A-F. The ICAO AA you provided did not meet this " \
            "criteria.")

    return jsonify(records)

# Search by ICAO Aircraft Address in hex format.
@app.route('/api/v1.0/icao-int/<icao_aa>', methods=['GET'])
def search_by_icao_aa_int(icao_aa):
    records = []
    results = {}

    if re.match(icao_aa_int_regex, icao_aa):
        results = db.search_icao_aa_int(int(icao_aa))

        for result in results:
            result.pop('_id')
            records.append(result)

        if results.count_documents() < 1:
            raise SearchResultNotFound("The ICAO address was not found in the FAA database.")

    else:
        raise InvalidSearchFormat("Integer ICAO aircraft 1 or more integers in lenth. " \
            "The ICAO AA you provided did not meet this criteria.")

    return jsonify(records)

# Trigger full FAA database ETL.
@app.route('/api/v1.0/faa-database', methods=['GET'])
def get_faa_db_etl():
    etl.download_faa_db()
    etl.decompress_faa_db()
    records = etl.process_decompressed_records()
    db.load_from_pandas_dataframe(records)

    return jsonify({'success': 'true'})

# Download the FAA database for later ETL.
@app.route('/api/v1.0/faa-database-zip', methods=['GET'])
def get_faa_db_zip():
    etl.download_faa_db()

    return jsonify({'success': 'true'})

# Run the FAA database ETL against an existing zip file.
@app.route('/api/v1.0/faa-database-etl', methods=['GET'])
def get_faa_db_etl_only():
    etl.decompress_faa_db()
    records = etl.process_decompressed_records()
    db.load_from_pandas_dataframe(records)

    return jsonify({'success': 'true'})


if __name__ == '__main__':
    app.run(debug=flask_debug, host=flask_host, port=flask_port)