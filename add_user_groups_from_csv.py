#!/usr/bin/env python3

# Reads a csv file and adds a Volunteer Hub user group for each row, except the first row. The first row
# is a header row, with the columns labeled:
#		"name," "parent_name," "description"
#
# The second and subsequenst rows must contain:
#	group name
#	parent group name
#	
#   A third field, description, is optional.
# 
# The easiest way to construct a suitable CSV file is to add the data to
# a spreadsheet and then save the spreadsheet as a CSV file.
# If the first row of the spreadsheet is labeled as indicated above, then
# the exported CSV file will have the correct structure.
#
# NOTE: The spelling must be exactly the same as the group in Volunteer Hub. However,
# the match is case-insenditive -- in the CSV file you may use upper or lower case,
# or any combination thereof, as desired.
#
# Read reservation expirations for VH events.
# For each one, print event id and value of reservation expiration drop-down select.
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
from fsvhub import UserGroupApi




if len(sys.argv) < 4:
	print("Usage: {} username password inputfile".format(sys.argv[0]))
	print("\tAny item containing spaces must be quoted.")
	sys.exit(1)
	
user = sys.argv[1]
password = sys.argv[2]
input_filename = sys.argv[3]



group_api = UserGroupApi(user,password)

with open(input_filename,'r') as infile:
	reader = csv.DictReader(infile)
	for row in reader:
		print(row)
		res = group_api.add_group(row['name'],
				 description=row['description'], parent_name=row['parent_name'])
		print(res)

group_api.logout()
