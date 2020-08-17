import csv
import datetime
from functools import lru_cache
import glob
import json
import os
import pathlib
from pprint import pprint
import re
import urllib.request
import zipfile

import pandas


class FaaDbETL:
    def __init__(self, clean_up=True):
        self.__clean_up = clean_up
        self.__faa_db_url           = "https://registry.faa.gov/database/ReleasableAircraft.zip"
        self.__faa_db_zip_file_name = "ac_db.zip"
        self.__faa_db_file_path     = "./tmp"
        self.__date_col_regex = re.compile(".+ DATE$")

        # All operations rely on our path existing.
        if os.path.isdir(self.__faa_db_file_path) is not True:
            pathlib.Path(self.__faa_db_file_path).mkdir(parents=True, exist_ok=True)


    @lru_cache(maxsize=1)
    def __get_faa_db_path(self):
        """ Generate the FAA database file path. """

        return "%s/%s" %(self.__faa_db_file_path, self.__faa_db_zip_file_name)
    
    def __clean_files(self):
        """ Clean up downloaded files. """

        tmp_files = glob.glob(self.__faa_db_file_path + "/*")

        self.print_log("Cleaning up temp files...")
        for tmp_file in tmp_files:
            os.remove(tmp_file)

    def __decompress_zip_file(self):
        """ Decompress the FAA database zip file. """
        db_file = self.__get_faa_db_path()

        self.print_log("Decompressing FAA dabase zip file...")
        with zipfile.ZipFile(db_file, 'r') as zip_ref:
            zip_ref.extractall(self.__faa_db_file_path)
    
    def __load_csv_as_df(self, csv_file):
        """ Load a CSV as a Pandas dataframe. """
        self.print_log("Loading %s..." %csv_file)
        df = pandas.read_csv(csv_file, encoding="utf-8")

        self.print_log("Strip whitespace from column names...")
        df.rename(columns=lambda x: x.strip(), inplace=True)

        for col_name in df:
            # Drop empty columns.
            if col_name.find("Unnamed: ") == 0:
                self.print_log("Drop empty column...")
                # We have to rename them before droping them because ...reasons.
                df.rename({col_name:"__drop__"}, axis="columns", inplace=True)
                df.drop(["__drop__"], axis=1, inplace=True)
                break

            # Strip whitespace.
            if df[col_name].dtype == object:
                self.print_log("Strip whitespace from %s..." %col_name)
                df[col_name] = df[col_name].str.strip()
        
            # We want to update N-NUMBERS everywhere we see them.
            if col_name == "N-NUMBER":
                self.print_log("Update N-NUMBER column data...")
                df[col_name] = "N" + df[col_name]
            
            # We want our matching columns expressed as strings.
            if col_name in ["CODE", "MFR MDL CODE", "ENG MFR MDL"]:
                self.print_log("Convert %s column to string to support merging..." %col_name)
                df[col_name] = df[col_name].astype(str).str.strip()
            
            if re.match(self.__date_col_regex, str(col_name)):
                self.print_log("Convert %s to date..." %col_name)
                df[col_name] = pandas.to_datetime(df[col_name])
            
            # Make sure we fill in "Nones" where Pandas nulls exist.
            df[col_name] = df[col_name].astype(object).where(df[col_name].notnull(), None)
            
        self.print_log("Rename columns to be uniform...")
        df.columns = df.columns \
            .str.strip() \
            .str.lower() \
            .str.replace(' ', '-') \
            .str.replace('(', '-') \
            .str.replace(')', '')

        return df

    def print_log(self, string):
        """ Print string with timestamp. """

        now = datetime.datetime.utcnow()
        now_str = datetime.datetime.strftime(now, '%Y-%m-%dT%H:%M:%S.%f+0000')
        print("%s - %s" %(now_str, string))

    def process_decompressed_records(self):
        """ Process decompressed database records """
        record_frame = []

        # Specify files to load.
        file_spec = {
            "master": {
                "file":   "MASTER.txt",
                "prefix": ""
            },
            "acftref": {
                "file":   "ACFTREF.txt",
                "prefix": "acft_"
            },
            "engine": {
                "file":   "ENGINE.txt",
                "prefix": "eng_"
            }
        }

        self.print_log("Extracting FAA database from files...")

        # Load each file up.
        for file in file_spec:
            self.print_log("Loading file %s..." %file)
            file_path = self.__faa_db_file_path + "/" + file_spec[file]['file']
            locals()[file] = self.__load_csv_as_df(file_path)
            self.print_log("Add prefix string to loaded file...")
            locals()[file].columns = file_spec[file]['prefix'] + locals()[file].columns

        # Merge master record and engine data.
        self.print_log("Merge master aircraft data with engine data...")
        record_frame = pandas.merge(locals()["master"], locals()["engine"],
            left_on='eng-mfr-mdl', right_on='eng_code', how='inner')

        # Merge master + engine data with aircraft reference data.
        self.print_log("Merge master and engine data with aircraft reference data...")
        record_frame = pandas.merge(record_frame, locals()["acftref"],
            left_on='mfr-mdl-code', right_on='acft_code', how='inner')

        # We don't need the merge columns anymore.
        self.print_log("Drop columns used to merge datasets...")
        record_frame.drop(["acft_code", "eng_code", "eng-mfr-mdl", "mfr-mdl-code"], axis=1, inplace=True)

        if self.__clean_up:
            self.print_log("Clean up triggered.")
            self.__clean_files()

        self.print_log("Extracted %s records." %len(record_frame.index))
        self.print_log("Database extract complete.")

        return record_frame

    def download_faa_db(self):
        """ Download the FAA database. """

        self.print_log("Downloading the FAA database ...")
        db_file = self.__get_faa_db_path()

        urllib.request.urlretrieve(self.__faa_db_url, db_file)

    def decompress_faa_db(self):
        """ Decompress the FAA database. """
        self.print_log("Beginning FAA database import.")
        self.__decompress_zip_file()
