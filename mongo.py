import datetime
from pprint import pprint

import pandas
import pymongo

class FaaDbMongo:
    def __init__(self, mongo_host, mongo_port, db_name="faa", coll_name="aircraft-registered"):
        self.__mongo_coll_name = coll_name
        self.__mongo_db_name = db_name
        self.__mongo_host = mongo_host
        self.__mongo_port = mongo_port

        self.__mongo_client = pymongo.MongoClient("mongodb://%s:%s/" %(mongo_host, mongo_port))
        self.__mongo_db = self.__mongo_client[db_name]
        self.__staging_coll = self.__mongo_db[coll_name + "_staged"]
        self.__registered_coll = self.__mongo_db[coll_name]
    
    def __filter_row(self, row_dict):
        """ Filter a given row before storage. """

        for item in row_dict:
            # If we have an empty string just remove the parameter.
            if row_dict[item] == "":
                row_dict[item] = None

        return row_dict

    def __swap_live_collection(self):
        """ After loading data into an intermediate collection migrate it to the main table. """

        # If we already have a collection
        if self.__mongo_coll_name in self.__mongo_db.collection_names():
            # Drop it.
            self.__registered_coll.drop()

        # Then renmae the staging collection to be the main one.
        self.__staging_coll.rename(self.__mongo_coll_name)

        # Refresh the refrence to the main collection.
        self.__registered_coll = self.__mongo_db[self.__mongo_coll_name]

        # Nuke the staging collection.
        self.__staging_coll.drop()

    def load_from_pandas_dataframe(self, data_frame):
        """ Load data from a Pandas dataframe. """
        records = data_frame.to_dict('records')

        for record in records:
            store = self.__filter_row(record)
            self.__staging_coll.insert_one(store)
        
        self.__swap_live_collection()

    def print_log(self, string):
        """ Print string with timestamp. """

        now = datetime.datetime.utcnow()
        now_str = datetime.datetime.strftime(now, '%Y-%m-%dT%H:%M:%S.%f+0000')
        print("%s - %s" %(now_str, string))

    def search_icao_aa_hx(self, icao_aa):
        """ Seach for aircraft by their hexidecimal ICAO AA. """

        docs = self.__registered_coll.find({'mode-s-code-hex': icao_aa})
        pprint(docs)
        
        return docs

    def search_icao_aa_int(self, icao_aa):
        """ Seach for aircraft by their integer ICAO AA. """

        docs = self.__registered_coll.find({'mode-s-code': icao_aa})
        pprint(docs)
        
        return docs
    
    def search_tail_number(self, tail_number):
        """ Seach for aircraft by their tail number. """

        docs = self.__registered_coll.find({'n-number': tail_number})
        pprint(docs)

        return docs