#!/usr/bin/env python3
#
# Reads a csv file and, for each row, carries out these actions:
#   * Adds team_name and org_name, to Volunteer Hub's user groups, if they don't already exist.
#       (The org_category user group must already exist.)
#   * creates landing page, if it doesn't already exist
#
# The first row of the csv file must be a header containing:
#   * team_name, for example, "Kroger - Jones". This is normally the org_name
#   + team leader's last name.
#   * org_name, for example, "Kroger." This is normally the name of the
#   corporation, school, or other organization that is sponsoring the team.
#   * org_category, for example 'Corporate Groups' or 'School Groups'.
#   * event_group. This will normally be 'All Events' However, a specific event
#   group such as 'Giving Fields,' 'Distribution Center,' or 'Food Room' may be
#   specified.
#   * leader_fname. First name of team leader
#   * leader_lname. Last name of team leader
#   * leader_username. May be blank; will be generated from lname and fname if
#   so.
#   * leader_password
#   * leader_work_phone. Leader's work phone number. Must be ten digits.
#   * leader_work_ext. Extension for leader's cell number. May be blank.
#   * leader_cell_phone. Leader's cell phone number. Must be ten digits.
#   * leader_home_phone. Leader's home phone number. Must be ten digits.
#   * leader_unk_phone. Leader's unspecified phone number. Must be ten digits.
#   * (All phone numbers may be blank.)
#   * leader_email. May be blank.
#   * leader_groups. Comma-delimited list of user groups to which this user
#   should belong, for example 'Team Leaders',  'Ohio Society of CPAs - Smith'
#       If this is blank, the user will be added to the user group
#       corresponding to team_name and to 'Team Leaders'.
#   * lp_name. Name of landing page to create. If this is blank, the name will
#   be generated by concatenating 'X - ' and the org_name, for example 'X -
#   Kroger.'
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
# This file and other files that are part of VolunteerHubWrapper are Copyright © 2018 by Tony Rein

import csv
#import os.path
#import re
import sys

#from selenium.webdriver.support.ui import Select
from fsvhub import UserApi, UserGroupApi, LandingPageApi, VhBrowser

class TransactionProcessor(object):
    def __init__(self,username,password,input_filename):
        self.input_filename = input_filename
        self.browser = VhBrowser(username,password)
        self.user_api = UserApi(self.browser)
        self.lp_api = LandingPageApi(self.browser)
        self.group_api = UserGroupApi(self.browser)
        self.req_fields = [
                    'team_name', 'org_name', 'org_category', 'event_group',
                        'leader_fname','leader_lname'
                    ]
        self.truth_markers = '1yYtT'

    def run(self):
        with open(self.input_filename,'r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if self.is_done(row):
                    print("Skipping this row")
                    print(row)
                else:
                    try:
                        self.process_row(row)
                    except Exception as e:
                        if "Required field" in e.__str__():
                            print(e) # alert user but don't abort loop
                            continue
                        else:
                            raise(e)
                #input('Press ENTER to continue...')

    def parse_row(self,row):
        # verify required fields present. While we're at it,
        # strip leading/trailing whitespace.
        for f in self.req_fields:
            s = row.get(f,'').strip()
            if s == '':
                raise Exception("Required field {} not present".format(f))
            else:
                row[f] = s # Substitute stripped value for original
        ret_data = { }
        ret_data['user_groups'] = { 'self': row['team_name'], 'parent':
                             row['org_name'],'grandparent': row['org_category'] }
        ret_data['event_group'] = row['event_group']
        # generate group list, if not explicitly given:
        s = row.get('leader_groups','').strip()
        if s == '':
            ret_data['leader'] = { 'groups': [ 'Team Leaders', row['team_name'] ] }
        else:
            ret_data['leader'] = { 'groups': s.split(',') }
        ret_data['leader']['fname'] = row['leader_fname']
        ret_data['leader']['lname'] = row['leader_lname']
        # Next set of fields can be blank or omitted, so use .get(field,'')
        # so there won't be an exception if the field isn't there.
        for f in [
        'username','password','work_phone','work_ext','home_phone',
            'cell_phone', 'unk_phone', 'email','skip']:
            ret_data['leader'][f] = row.get('leader_' + f,'').strip()
        if ret_data['leader']['username'] == '':
            # Generate leader's user_name, if not given in data file.
            ret_data['leader']['username'] = ret_data['leader']['fname'] + ' ' + ret_data['leader']['lname']
        # See if we have a landing page name...
        pname = row.get('lp_name','').strip()
        # If not, generate it from parent group's name...
        if pname == '':
            pname = 'X - {}'.format(ret_data['user_groups']['parent'])
        ret_data['landing_page'] = { 'name': pname }
        desc = self.generate_description(ret_data)
        ret_data['user_groups']['description'] = desc
        return ret_data

    def generate_description(self, data):
        s = "{} 2016. Contact {} {}.".format(
                                data['event_group'], data['leader']['fname'],
                                data['leader']['lname'])
        s += " Telephone: "
        wp = data['leader']['work_phone']
        wpx = data['leader']['work_ext']
        hp = data['leader']['home_phone']
        cp = data['leader']['cell_phone']
        up = data['leader']['unk_phone']
        if wp != '':
            s += wp + ' '
            if wpx != '':
                s += 'x' + wpx
            s += '(o).'
        s += (' ' + cp + ' (c).') if cp != '' else ''
        s += (' ' + hp + ' (h).') if hp != '' else ''
        s += (' ' + up + '.') if up != '' else ''
        if data['leader']['email'] != '':
            s += ' Email: ' + data['leader']['email']
        return s

    def do_groups(self,groupdata):
        grandparent = groupdata['grandparent']
        parent = groupdata['parent']
        user_group = groupdata['self']
        description = groupdata['description']
        print("Processing group {}".format(user_group))
        print("Description: {}".format(description))
        if not self.group_api.group_exists(grandparent):
            raise Exception("Top-level group (eg 'Corporate Groups' or 'School Groups') not found.")
        print("Top-level group {} exists.".format(grandparent))
        if not self.group_api.group_exists(parent):
            print("Calling 'group_api.add_group({},parent_name={})'".format(parent,grandparent))
            self.group_api.add_group(parent,parent_name=grandparent)
        if not self.group_api.group_exists(user_group):
            print("Calling 'group_api.add_group({},parent_name={},description={})'".format(user_group,parent,description) )
            self.group_api.add_group(user_group,parent_name=parent,description=description)

    def do_landing_page(self,data):
        gname = data['user_groups']['parent']
        pname = data['landing_page']['name']
        print("Page name: {}".format(pname))
        if not self.lp_api.page_exists(pname):
            print("Adding landing page for organization {}".format(gname))
            self.lp_api.add_landing_page(data['user_groups']['parent'],
                 gname, pname, data['event_group'])
        else:
            print("Skipping landing page for group {} - it already exists".format(gname))

    def do_user(self,userdata):
        print("User data: {}".format(userdata))
        if self.skip_user(userdata):
            return { 'result': 'Data input requires skipping user {}'.format(userdata['username']) }
        if self.user_api.user_exists(userdata['username']):
            return { 'result': 'User {} already exists -- not adding'.format(userdata['username']) }
        else:
            print("Adding user {}".format(userdata['username']))
            try:
                return self.user_api.add_user(data=userdata)
            except Exception as e:
                if 'Cannot add user' in e.__str__(): # invalid input
                    return { 'result': e.__str__() }
                else:
                    raise(e)

    def process_row(self,row):
        data = self.parse_row(row)
        team_name = data['user_groups']['self']
        print("Processing group {}".format(team_name))
        print(data)
        self.do_groups(data['user_groups'])
        self.do_landing_page(data)
        print(self.do_user(data['leader']))

    def logout(self):
        self.browser.logout()

    def is_done(self,data):
        return self.field_is_true(data, 'complete')

    def skip_user(self,userdata):
        return self.field_is_true(userdata,'skip')

    def field_is_true(self,data,fieldname):
        s = data.get(fieldname,'').lstrip()
        if s == '':
            return False
        else:
            return s[0] in self.truth_markers

def main():
    if len(sys.argv) < 4:
        print("Usage: {} username password inputfile".format(sys.argv[0]))
        print("\tAny item containing spaces must be quoted.")
        sys.exit(1)
    tp = TransactionProcessor(sys.argv[1], sys.argv[2],sys.argv[3])
    try:
        tp.run()
    finally:
        tp.logout()

if __name__ == '__main__':
    main()
