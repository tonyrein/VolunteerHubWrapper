#!/usr/bin/env python3
#
# Reads a csv file and, for each row, carries out these actions:
#	* adds any user groups in that row which don't already exist
#	* creates landing page, if page doesn't already exist
#		(if this page already exists, the csv file must note that, as this
#		code cannot (yet) check, and an error will result if an attempt
#		is made to add a page using a nme already in use.)
#
# The first row of the csv file must be a header containing:
#	* user_group
#	* parent_group
#	* grandparent_group (eg 'Corporate Groups' or 'School Groups')
#	* event_group ('Giving Fields,' 'Distribution Center,' or 'All Events')
#	* leader_fname
#	* leader_lname
#	* leader_username (may be blank; will be generated from lname and fname if so)
#	* leader_password
#	* leader_cell (may be blank)
#	* leader_home (may be blank)
#	* leader_email (may be blank)
#	* leader_groups (comma-delimited list of user groups to which this user should belong)
#		(May be blank; if so, this user will be added to the user_group named above and to 'Team Leaders.')
#	* lp_name (may be blank; if so, will be generated from user_group)
#	* lp_exists ('1', 'Y', 'y', 'yes', 'Yes', 'YES', etc. will mean True. Anything else means False)
#


#	a list of groups names, separated by commas; for example, 
#		group1, group 2, third group, All Users, Team Leaders
#
# 
# The easiest way to construct a suitable CSV file is to add the data to
# a spreadsheet and then save the spreadsheet as a CSV file.
# If the first row of the spreadsheet is labeled as indicated above, then
# the exported CSV file will have the correct structure.
#
# NOTE: The groups listed in the groups column must already exist. In addition,
# the spelling must be exactly the same as the group in Volunteer Hub. However,
# the match is case-insenditive -- in the CSV file you may use upper or lower case,
# or any combination thereof, as desired.
#
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
from fsvhub import UserApi, UserGroupApi, LandingPageApi


def parse_row(row):
	# verify required fields present
	req_fields = [ 
				'user_group', 'parent_group', 'grandparent_group', 'event_group',
					'leader_fname','leader_lname','leader_password'
				]
	for f in req_fields:
		if row.get(f,'').strip() == '':
			raise Exception("Required field {} not present".format(f))
	# generate group list, if not explicitly given:
	s = row.get('leader_groups','').strip()
	if s == '':
		row['leader_groups'] = [ 'Team Leaders', row['user_group'] ]
	else:
		row['leader_groups'] = s.split(',')
	# generate user group description:
	row['user_group_description'] = "{} 2016. Contact {} {}. Phone {}. Email {}".format(
			row['event_group'], row['leader_fname'], row['leader_lname'], row['leader_cell'],
			row['leader_email']
			)
	return row

	def do_groups(group_api,group,description,parent,grandparent):
		if not group_api.group_exists(grandparent):
			raise Exception("Top-level group (eg 'Corporate Groups' or 'School Groups' not found.")
		if not group_api.group_exists(parent):
			group_api.add_group(parent,parent_name=grandparent)
		if not group_api.group_exists(group):
			group_api.add_group(group,parent_name=parent,description=description)			

def main():
	if len(sys.argv) < 4:
		print("Usage: {} username password inputfile".format(sys.argv[0]))
		print("\tAny item containing spaces must be quoted.")
		sys.exit(1)
		
	user = sys.argv[1]
	password = sys.argv[2]
	input_filename = sys.argv[3]
	
	
	
	user_api = UserApi(user,password)
	group_api = UserGroupApi(user,password)
	lp_api = LandingPageApi(user,password)
	
	with open(input_filename,'r') as infile:
		reader = csv.DictReader(infile)
		for row in reader:
			try:
				data = parse_row(row)
			except Exception as e:
				print(e)
				continue
			try:
				do_groups(group_api, data['user_group'], data['user_group_description'],
					data['parent_group'], data['grandparent_group'])
			except Exception as e:
				print(e)
				continue
			
			# change groups to list...
			s = row['leader_groups']
			if s.strip() == '':
				row['groups'] = [ 'Team Leaders']
			row['groups'] = s.split(',')
			print(row)
			try:
				user_api.add_user(data=row)
			except Exception as e:
				# If exception is other than name already in use,
				# re-raise it. Otherwise, igonore it.
				if not 'already in use' in e.__str__():
					raise(e)
				
	
	user_api.logout()

if __name__ == '__main__':
	main()
