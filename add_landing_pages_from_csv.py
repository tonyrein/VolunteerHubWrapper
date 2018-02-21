#!/usr/bin/env python3

# Reads a csv file and adds a Volunteer Hub landing for each row, except the first row. The first row
# is a header row, with the columns labeled:
#	"name"
#	"organization_name"
#	"user_group_name"
#	"event_group"
#
# All fields are required, except for event_group -- event_group
# will default to "All Events" if omitted.
# 
# The easiest way to construct a suitable CSV file is to add the data to
# a spreadsheet and then save the spreadsheet as a CSV file.
# If the first row of the spreadsheet is labeled as indicated above, then
# the exported CSV file will have the correct structure.
#
# NOTE: The spelling must be exactly the same as in the corresponding Volunteer Hub field.
# However, the match is case-insensitive -- in the CSV file you may use upper or lower case,
# or any combination thereof, as desired.
#
# Uses built-in re and sys modules.
#
# Uses selenium (third party, available via PyPi)
#
# Uses fsvhub and config file vhconfig.cfg
#
import csv
import os.path
import re
import sys

from selenium.webdriver.support.ui import Select
from fsvhub import LandingPageApi, VhBrowser


if len(sys.argv) < 4:
	print("Usage: {} username password inputfile".format(sys.argv[0]))
	print("\tAny item containing spaces must be quoted.")
	sys.exit(1)
	
user = sys.argv[1]
password = sys.argv[2]
input_filename = sys.argv[3]

b = VhBrowser(user,password)
api = LandingPageApi(b)

with open(input_filename,'r') as infile:
	reader = csv.DictReader(infile)
	for row in reader:
		print(row)
		api.add_landing_page(row['organization_name'], row['user_group'],
        page_name=row['page_name'], event_group=row['event_group'])

api.logout()
