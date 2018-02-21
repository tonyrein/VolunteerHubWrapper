#!/usr/bin/env python3

# Read reservation expirations for VH events.
# For each one, print event id and value of reservation expiration drop-down select.
#
# Uses built-in re and sys modules.
#
# Uses selenium (third party, available via PyPi
#
# Uses fsvhub and config file vhconfig.cfg
#

import re
import sys

from selenium.webdriver.support.ui import Select
from fsvhub import VhConfig, VhBrowser

if len(sys.argv) != 3:
	print("You must supply a user name and password. If either one contains spaces, you must use quotes around it.")
	sys.exit(1)
	
user = sys.argv[1]
password = sys.argv[2]
c = VhConfig(user,password,config_file='vhconfig.cfg')
b = VhBrowser(c)
index_url = c.event['INDEX_URL']
summ_url = c.event['SUMMARY_URL']
reg_users_url = c.event['REG_USERS_URL']
patt=re.compile(c.event['SEL_EXPIRATION_REGEX'])

b.goto(index_url)
# Give page time to load
b.wait_for_element('Footer')

# list of all links on page
all_links = b.find_list_by_css('a')
# Filter for those linking to events...
event_links = [ l for l in all_links if l.get_attribute('href') and 
	l.get_attribute('href').startswith(summ_url) ]

# Get list of event ids...
event_ids = [ l.get_attribute('href').split('=')[-1] for l in event_links ]

# For each event id, open that event's "Registered Users" page, get a list of all 'select' tags, then
# narrow that list to only those with an id that matches our regex.
for eid in event_ids:
	b.goto( reg_users_url + eid)
	b.wait_for_element(c.event['BTN_SAVE_REGISTRATION'])
	
	all_sel_tags = b.find_list_by_css('select')
	expiration_sel_tags = [ t for t in all_sel_tags
		if patt.match(t.get_attribute('id')) ]

	# For each expiration_sel_tag, print the event id and the selected text...
	for sel_tag in expiration_sel_tags:
		# Wrap select tag in a selenium Select object...
		sel = Select(sel_tag)
		t = sel.first_selected_option.text
		print("{}: {}".format(eid,t))

b.logout()
