#!/usr/bin/env python3

# For each event:
#  go to "Registered Users" page
#  clear "Allow Overflow checkboxes
#
#  The relevant checkboxes can be identified because they have
#	ids similar to '#Main_UnderMainBar_UnderSubBar_UnderObjectBar_Subevents_Registration_0_EventPanel_0_ctl01_0_UserGroupRegistrations_0_UserGroupItem_0_AllowOverflow_0'
#
#  The date of the event is on the "Registered Users" page, contained
#    in a div.Times in the format %A, %B %e, %Y, if not in current year, or
#		%A, %B %-d, if in current year. For example, if today's date is
#		April 3, 2016, an event on September 22, 2016 would have the date as
#		"Thursday, September 22," and an event a year later would have the
#		date as "Friday, September 22, 2017,"
#		The two cases can be distinguished by regex. If the date string
#		matches "[a-zA-Z]+,\s[a-zA-Z]+\s\d{1,2},\s\d{4}" then we're not in the
#		current year.
#		In the case we're not in the current year, 
#		
# Uses built-in datetime, re and sys modules.
#
# Uses selenium (third party, available via PyPi
#
# Uses fsvhub and config file vhconfig.cfg
#

import datetime
import re
import sys

from selenium.webdriver.support.ui import Select
from fsvhub import VhConfig, VhBrowser, Util

class OverFlower(object):
	def __init__(self, argstring):

		if len(argstring) < 3:
			print("You must supply a user name and password. If either one contains spaces, you must use quotes around it.")
			sys.exit(1)
		self.user = argstring[1]
		self.password = argstring[2]
		if len(argstring) > 3:
			self.otheryear_regex = re.compile("[a-zA-Z]+,\s[a-zA-Z]+\s\d{1,2},\s\d{4}")
			self.thisyear_regex = re.compile("[a-zA-Z]+,\s[a-zA-Z]+\s\d{1,2}") 
			self.event_date_pattern = '%A, %B %d, %Y'
			self.cmd_line_date_pattern = '%Y-%m-%dT%H:%M'
			self.startdate = datetime.datetime.strptime(argstring[3], self.cmd_line_date_pattern)
			if len(argstring) > 4:
				self.enddate = datetime.datetime.strptime(argstring[4], self.cmd_line_date_pattern)
			else:
				self.enddate = None
		else:
			self.startdate = None
			self.enddate = None
		
		 
	
	def get_date_from_event_text(self, event_text):
		# Are we in another year or this year?
		match = self.otheryear_regex.search(event_text)
		if match: # another year...
			return datetime.datetime.strptime(match.group(0), self.event_date_pattern)
		else: # this year -- we have to supply the year portion of the date string...
			match = self.thisyear_regex.search(event_text)
			year = datetime.datetime.now().year
			s = "{}, {}".format(match.group(0), year)
			return datetime.datetime.strptime(s, self.event_date_pattern)

		#
		# usage: prog username password [startdate [enddate] ]
		# example: prog "joe smith" "secret" 2016-04-02T00:00:00 2016-06-30T00:00:00"
		#
	def run(self):
		b = VhBrowser(self.user,self.password)
		index_url = b.cfg.event['INDEX_URL']
		summ_url = b.cfg.event['SUMMARY_URL']
		reg_users_url = b.cfg.event['REG_USERS_URL']
		patt = re.compile(b.cfg.event['CHK_ALLOW_OVERFLOW_REGEX'])
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
		
		# For each event id, open that event's "Registered Users" page, get a list of all 'input' tags, then
		# narrow that list to only those with an id that matches our regex.
		for eid in event_ids:
			b.goto( reg_users_url + eid)
			
			b.wait_for_element(b.cfg.event['BTN_SAVE_REGISTRATION'])
			if self.startdate: # check if this is in our date range
				print("Checking dates...")
				date_div = b.find_element_by_css('div.Times > nobr:nth-child(1)')
				event_text = date_div.get_attribute('innerHTML')
				event_date = self.get_date_from_event_text(event_text)
				print("Event: {} Start: {}".format(event_date,self.startdate))
				if event_date < self.startdate:
					print("Skipping -- event before startdate")
					continue
				else:
					if self.enddate:
						print("End: {}".format(self.enddate))
						if event_date > self.enddate:
							print("Skipping -- event after enddate")
							continue
				print("Date is in range -- processing")
			else:
				print("No dates specified")
				
			all_input_tags = b.find_list_by_css('input')
			for t in all_input_tags:
				if patt.search(t.get_attribute('id')):
					Util.turn_off(t)
		
		b.logout()


def main():
	o = OverFlower(sys.argv)
	o.run()
	
if __name__=='__main__':
	main()
