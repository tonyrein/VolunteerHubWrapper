
import configparser
import datetime
import os.path
import re

import requests

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

class VhConfig(object):
    def __init__(self,user,password,config_file='vhconfig.cfg'):
        self.username = user
        self.password = password
        self.cfg = configparser.SafeConfigParser(interpolation=None)
        config_files_read = self.cfg.read(config_file)
        if len(config_files_read) == 0:
            raise Exception('Could not find config file {}'.format(config_file))
        # For convenience, make sections of self.cfg attributes of self:
        for s in self.cfg.sections():
            setattr(self, s.lower(), self.cfg[s])


class VhRest(object):
    """
    frontend to Volunteer Hub's published REST API. For info, see:
    http://support.volunteerhub.com/Knowledgebase/List/Index/4/application-programmer-interface-api

    This class is a singleton.

    """
    __instance = None
    def __new__(cls,cfg):
        if VhRest.__instance is None:
            VhRest.__instance = object.__new__(cls)
            VhRest.__instance.cfg = cfg
            VhRest.__instance._users = None
            VhRest.__instance._event_groups = None
            VhRest.__instance._user_groups = None
            VhRest.__instance.base_url = VhRest.__instance.cfg.api['BASE_URL']
        return VhRest.__instance

    @property
    def users(self):
        if self._users is None:
            self.get_user_list()
        return self._users

    @property
    def event_groups(self):
        if self._event_groups is None:
            self.get_event_group_list()
        return self._event_groups

    @property
    def user_groups(self):
        if self._user_groups is None:
            self.get_user_group_list()
        return self._user_groups

    def add_event_group_from_json(self,j):
        gid = j['EventGroupUid']
        self._event_groups[gid] = { 'name': j['Name'],
                'parent_id': j.get('ParentEventGroupId', None) }

    def get_event_group_list(self):
        self._event_groups = {}
        self.get_vh_list(api_call='v1/eventGroups', data={},
            func=self.add_event_group_from_json)

    def get_event_list(self, starting=None, stopping=None):
        """
        We cannot handle this as the way the users, user_groups,
        and event_groups properties are handled, because we
        have to be able to specify starting and stopping dates.
        If starting is None, default to today at 12:00:00 am.
        If stopping is None, default to getting all events from
        starting on, with no end date.
        starting and stopping, if supplied, must be in ISO8601
        format, that is YYYY-MM-DDTHH:MM:SS, for example
        "2016-03-31T00:00:00"
        """
        ret_list = []
        if starting is None:
            d = datetime.datetime.now().date()
            starting = d.isoformat() + "T00:00:00"
        # Define callback function to pass to get_vh_list:
        def add_event_from_json(j):
            ret_list.append(j)
        data={ 'query': 'Time', 'earliestTime': starting }
        if stopping is not None:
            data['latestTime'] = stopping
        print(data)
        self.get_vh_list(api_call='v1/events', data=data,func=add_event_from_json)
        return ret_list

    def event_group_name_from_id(self, gid):
    #   if not gid or not gid in self.event_groups:
        if not gid:
            return None
        else:
            # if no such event group, set it to an empty dict
            eg = self.event_groups.get(gid,{})
            # if eg is empty, next line will return None
            return eg.get('name',None)
            #return self.event_groups[gid]['name']

    def event_group_id_from_name(self,gname):
        for k in self.event_groups.keys():
            if self.event_groups[k]['name'] == gname:
                return k
        return None

    def event_group_parent_name(self,gname):
        gid = self.event_group_id_from_name(gname)
        n = self.event_group_name_from_id(self.event_groups[gid]['parent_id'])
        return n if n else None

    def add_user_group_from_json(self,j):
        gid = j['UserGroupUid']
        self._user_groups[gid] = { 'name': j['Name'], 'description': j['Description'],
                'parent_id': j.get('ParentUserGroupUid', None) }

    def get_user_group_list(self):
        self._user_groups = {}
        self.get_vh_list(api_call='v1/userGroups', data={},
            func=self.add_user_group_from_json)

    def user_group_name_from_id(self, gid):
        #if not gid or not gid in self.user_groups:
        #    return None
        #return self.user_groups[gid]['name']
        if not gid:
            return None
        else:
            # if no such user group, set it to an empty dict:
            ug = self.user_groups.get(gid,{})
            # if ug is empty, next line will return None:
            return ug.get('name',None)


    def user_group_id_from_name(self,gname):
        for k in self.user_groups.keys():
            if self.user_groups[k]['name'] == gname:
                return k
        return None

    def user_group_parent_name(self,gname):
        gid = self.user_group_id_from_name(gname)
        pid = self.user_groups['gid'].get('parent_id',None)
        return self.event_group_name_from_id(pid)
        #return self.event_group_name_from_id(self.user_groups[gid]['parent_id'])
        #return n if n else None

    def add_temp_user_group(self,user_group_name, parent_group_name, description):
        """
        If the UserGroupApi adds a group, we won't know the group id
        yet -- that is assigned internally by Volunteer Hub's backend.
        But we need to record the fact that this name is taken. We can
        do that by re-running get_user_group_list(), but it may be cheaper
        just to generate a unique id with the timestamp and use that
        as this group's id.

        This will fail silently in the unlikely event that two clients add the same
        group name within the same millisecond!

        The temp group added here will be stored in-RAM only, not in
        the Volunteer Hub database. This in-RAM store will be overwritten
        by the next call to get_user_group_list().

        """
        temp_id = 'TMP_UID_' + datetime.datetime.now().isoformat()
        parent_id = self.user_group_id_from_name(parent_group_name)
        self.user_groups[temp_id] = { 'name': user_group_name,
                                        'parent_id': parent_id, 'description': description }

    def user_name_from_id(self, uid):
        #if not uid or not uid in self.users:
        #    return None
        #else:
        #    return self.users[uid]['username']
        if not uid:
            return None
        else:
            # if no such user, set it to an empty dict:
            u = self.users.get(uid,{})
            # if u is empty, next line will return None:
            return u.get('username',None)

    def user_id_from_username(self,username):
        for k in self.users.keys():
            if self.users[k]['username'] == username:
                return k
        return None

    def add_user_from_json(self,u):
        d = {}
        d['username'] = u['Username']
        d['group_ids'] = u['UserGroupMemberships']
        """
        TODO: Fix this bug. The next part will get the first and
        last names of the emergency contact, instead of those of
        the user, at least sometimes.
        """
        for a in u['FormAnswers']:
            if 'LastName' in a:
                d['last_name'] = a['LastName']
                d['first_name'] = a['FirstName']
                break
        uid = u['UserUid']
        self._users[uid] = d

    def get_user_list(self):
        self._users = {}
        self.get_vh_list(api_call='v2/users', data={ 'query': 'LastUpdate', 'earliestLastUpdate': '1970-01-01T00:00:00' },
            func=self.add_user_from_json)

    def get_vh_list(self, api_call='', data={}, func):
        """
        Performs repeated (scrolling) call to VH Rest API
        to retrieve desired data.
        Pass:
            api_call (string) -- which api call to make
            data (dict) -- any parameters, other than page number and number
                of records per page, required by the api call
            func (function or method) -- handler for the results of each
                call to VH

        Example use:
            data_dict = { 'query': 'LastUpdate', 'earliestLastUpdate': '1970-01-01T00:00:00' }
            self.get_vh_list(api_call='v2/users', data=data_dict, func=self.add_user_from_json)

        """
        # How many should we get in each chunk?
        records_per_page = self.cfg.api.getint('REC_PER_PAGE')
        data['pageSize'] = records_per_page
        # Add page parameters to passed-in data dict...
        page_number = 0
        while True:
            data['page'] = page_number
            # Construct and submit http request to VH server to get
            # "pageSize" records...
            r = requests.get( self.base_url + api_call, params=data, auth=(self.cfg.username,self.cfg.password))
            if r.status_code != 200:
                raise Exception('Failure calling VolunteerHub API')
            # Process each item in returned JSON...
            # Does it even make sense to have func==None?
            j = r.json()
            if func != None:
                for rec in j:
                    func(rec)
            # Are we done?
            if len(j) < records_per_page:
                break
            else:
                page_number += 1 # Not done - go to next chunk

class VhBrowser(object):
    """
    Handles actual web interactions with VH site, especially
    opening URLs.
    Clients can use this to get page elements if needed,
    but whenever possible interactions with web pages
    should be handled internally in this class.
    """
    def __init__(self,username,password,visible=True):
        self.cfg = VhConfig(username,password)
        self.visible = visible
        self.browser = None
        self.display = None
        self.old_window_handle = None
        self.vr = VhRest(self.cfg)

    def switch_to_newest_window(self):
        self.browser.switch_to_window(self.browser.window_handles[-1])

    def save_window_handle(self):
        self.old_window_handle = self.browser.current_window_handle

    def return_to_previous_window(self):
        if self.old_window_handle is not None:
            self.browser.switch_to_window(self.old_window_handle)
            self.old_window_handle = None

    def wait_for_element(self, el_id, timeout=10):
        try:
            ret_element = WebDriverWait(self.browser, timeout).until(
                    EC.presence_of_element_located( (By.ID, el_id) )
                )
            return ret_element
        except:
            return None

    def wait_for_element_by_css(self, css_spec, timeout=10):
        try:
            ret_element = WebDriverWait(self.browser, timeout).until(
                    EC.presence_of_element_located( (By.CSS_SELECTOR, css_spec) )
                )
            return ret_element
        except:
            return None

    def wait_for_element_to_disappear(self, el_id, timeout=10):
            WebDriverWait(self.browser, timeout).until(
                EC.staleness_of(el_id)
                );

    def find_list_by_css(self,css_spec):
        return self.browser.find_elements_by_css_selector(css_spec)

    def find_element_by_css(self,css_spec):
        return self.browser.find_element_by_css_selector(css_spec)

    def find_list_by_xpath(self, xpath_spec):
        return self.browser.find_elements_by_xpath(xpath_spec)

    def find_element_by_xpath(self,xpath_spec):
        return self.browser.find_element_by_xpath(xpath_spec)

    def goto(self,url):
        if self.browser is None:
            self.login_to_vh()
        self.browser.get(url)

    def login_to_vh(self):
        """
        Log in to FSFB VH.
        Sets self.browser and self.main_window_handle
        Throws exception if:
          * open main VH page error
          * login error
          * problem finding controls (username or password fields, signin button)
            or signin link
        """
        # Create a virtual display and an automated browser:
        self.display = Display(visible=self.visible,size=(800,600))
        self.display.start()
        binary = FirefoxBinary('PATH TO FIREFOX BINARY')
        self.browswer = webdriver.Firefox(firefox_binary=binary)
        # Open login page:
        self.browser.get(self.cfg.login['URL'])
        # Proceed only when the required controls are present:
        login_button = self.wait_for_element(self.cfg.login['BUTTON'])
        uname_field = self.wait_for_element(self.cfg.login['TXT_USER'])
        pwd_field = self.wait_for_element(self.cfg.login['TXT_PASSWORD'])
        if login_button is None or uname_field is None or pwd_field is None:
            self.logout()
            raise Exception('Could not log in to Volunteer Hub!')
        # Fill in user name and password, and click login button:
        uname_field.send_keys(self.cfg.username)
        pwd_field.send_keys(self.cfg.password)
        login_button.click()
        self.wait_for_element_to_disappear(login_button)
        self.main_window_handle = self.browser.current_window_handle

    def logout(self):
        if self.browser is not None:
            self.browser.quit()
            self.browser = None
        if self.display is not None:
            self.display.stop()
            self.display = None

class Util(object):
    @staticmethod
    def turn_on(checkbox):
        if not checkbox.is_selected():
            checkbox.click()
    @staticmethod
    def turn_off(checkbox):
        if checkbox.is_selected():
            checkbox.click()

    @staticmethod
    def minify(s):
        """
        Remove all but alphanumeric and change to lower-case
        """
        return ''.join([i for i in s if i.isalnum()]).lower()

    @staticmethod
    def select_in_dropdown_by_partial_text(select_element, s):
        """
        VH uses '...' to indent subcategories in some selects controls
        """
        match_found = False
        for o in select_element.options:
            # use lstrip() to get rid of leading '...'
            # use upper() to make this case-insensitive...
            if o.text.lstrip('.').upper() == s.upper():
                match_found = True
                o.click()
                break
        if not match_found: # select first element if no match
            select_element.select_by_index(0)

##
# TODO: Change into Singleton
##
class UserApi(object):
    def __init__(self, vh_browser):
        self.vh_browser = vh_browser
        self.cfg = self.vh_browser.cfg

    def logout(self):
        self.vh_browser.logout()

    def user_exists(self, username):
        """
        Returns user id if user is present; else returns None
        """
        return self.vh_browser.vr.user_id_from_username(username)


    def select_user_groups(self, group_list):
        """
        Assumes that we are on a user add or user edit page.
        Checks the checkboxes corresponding to the groups in group_list
        and unchecks all other groups' checkboxes.
        """
        # Find list of spans within group manager div:
        spans = self.vh_browser.find_list_by_css(self.cfg.user['DIV_UG_MGR'] + ' span')
        # Make a copy of group_list, with each element stripped of leading and trailing spaces,
        # and converted to upper case...
        GL = [ v.strip().upper() for v in group_list ]
        # Now check text of each span against group name in group_list.
        # Check the corresponding checkboxes of the matches; uncheck
        # the rest:
        for s in spans:
            # Find checkbox controls contained in this span's parent...
            cb = s.find_element_by_xpath('..').find_element_by_css_selector('input[type="checkbox"')
            if s.text.strip().upper() in GL:
                Util.turn_on(cb)
            else:
                Util.turn_off(cb)


    """
    Find the url for the edit page for given username.
    If there is no user with this username, return None

    1. go to http://VOL_HUB_CUSTOMER.volunteerhub.com/Users
    2. find element id 'q'
    3. find search button (input type="submit" value="Search")
    4. type in username and click search button

    """
    def find_user_edit_url(self,username):
        pass

    """
    Need to add code to insert a temporary user (id not known)
    into self.vh_browser.vr._users.
    """
    def add_user(self, data={}):
        print("add_user called with following data:")
        print(data)
        """
        Assumes VhBrowser (self.vh_browser) is already instantiated
        data is a dict containing the fields for this user, for example:
        {  'username': 'joejones23',
        'fname': 'Joe', 'lname': 'Jones', 'password': 'SuperSecret',
            'groups': "Team Leaders, Duck-Billed Dinosaurs ],
            'cell_phone_number': '555-555-5555', 'home_phone_number': '321-555-1212' }
        Either username or at least one of fname or lname must be given.
        If username is not given, a username will be constructed by
        concatenating the first name plus a space plus the last name.

        In any case, the username will be stripped of any trailing or leading
        spaces before use.

        If the username (whether passed explicitly or constructed from the person's names)
        already exists, this method will fail, raising Exception('Name already in use.')

        If username, fname, and lname are all omitted the method will raise
        ValueError("If username is not omitted, at least one of fname or lname must be given.")

        FIELDS SUPPORTED:
            usernmae
            password
            fname
            lname
            home_phone_number - phone numbers must have 10 digits
            cell_phone_number
            email
            groups
        """
        # First, verify data integrity and determine the username:
        username = data.get('username','').strip()
        fname = data.get('fname','').strip()
        lname = data.get('lname','').strip()
        if username == '':
            if fname == '' and lname == '': # Both names either omitted or zero-length
                raise ValueError("Cannot add user - no username, last name, or first name found.")
            else:
                username = (fname + ' ' + lname).strip()
        # username already in use?
        if self.user_exists(username):
            raise Exception("Cannot add user {} - user already exists.".format(username))

        # Go to add user page..
        self.vh_browser.goto(self.cfg.user['ADD_URL'])
        # make sure page has loaded by waiting for "save" button...
        save_button = self.vh_browser.wait_for_element_by_css('input[value="Save User"]')
        # Get list of input elements on this page:
        inputs = []
        try:
            inputs = self.vh_browser.browser.find_elements_by_tag_name('input')
        except:
            raise Exception("No input tags found on page!")
        # Find username field. If present, put in username:
        flds = [ i for i in inputs if i.get_attribute('id') == self.cfg.user['TXT_USER_NAME'] ]
        if len(flds) != 1:
            raise Exception("Could not find username input field. Perhaps the page structure has changed.")
        username_field = flds[0]
        try:
            username_field.click()
            username_field.send_keys(username)
        except:
            raise Exception("Could not find username input field. Perhaps the page structure has changed.")

        password = data.get('password','')
        print("Value of password: {}".format(password))
        if password != '':
            try:
                password1_field = [ i for i in inputs if i.get_attribute('id') == self.cfg.user['TXT_PASSWORD'] ][0]
                password1_field.click()
                password1_field.send_keys(password)
            except:
                raise Exception("Could not find password input field. Perhaps the page structure has changed.")
            try:
                password2_field = [ i for i in inputs if i.get_attribute('id') == self.cfg.user['TXT_VERIFY_PASSWORD'] ][0]
                password2_field.click()
                password2_field.send_keys(password)
            except Exception as e:
                raise e
        if fname != '':
            flds = [ i for i in inputs if i.get_attribute('id') == self.cfg.user['TXT_FIRST_NAME'] ]
            if len(flds) != 1:
                raise Exception("Could not find first name input field. Perhaps the page structure has changed.")
            firstname_field = flds[0]
            try:
                firstname_field.click()
                firstname_field.send_keys(fname)
            except Exception as e:
                raise e

        if lname != '':
            try:
                lastname_field = [ i for i in inputs if i.get_attribute('id') == self.cfg.user['TXT_LAST_NAME'] ][0]
                lastname_field.click()
                lastname_field.send_keys(lname)
            except:
                raise Exception("Could not find last name input field. Perhaps the page structure has changed.")

        home_number = data.get('home_phone', '')
        if home_number != '':
            try:
                s = "home.*phone.*number"
                home_prompt = [ p for p in self.vh_browser.find_list_by_css('div.subprompt') if re.search(s,p.text,re.IGNORECASE) ][0]
                home_container = home_prompt.find_element_by_xpath("following-sibling::*[1]")
                home_input = home_container.find_element_by_xpath('.//input')
                home_input.click()
                home_input.send_keys(home_number)
            except:
                raise Exception("Could not find home phone input field. Perhaps the page structure has changed.")

        cell_number = data.get('cell_phone','')
        if cell_number != '':
            # Locate cell phone input text field. This
            # is somewhat indirect!
            try:
                s = "cell.*number"
                cell_prompt = [ p for p in self.vh_browser.find_list_by_css('div.prompt') if re.search(s,p.text,re.IGNORECASE) ][0]
                cell_container = cell_prompt.find_element_by_xpath("following-sibling::*[2]")
                cell_input = cell_container.find_element_by_xpath('.//input')
                cell_input.click()
                cell_input.send_keys(cell_number)
            except:
                raise Exception("Could not find cell phone input field. Perhaps the page structure has changed.")

        groups_to_join = data.get('groups', [])
        if len(groups_to_join) > 0:
            self.select_user_groups(groups_to_join)

        save_button.click()
        return { 'result': 'user_added: {}'.format(username)}


class UserGroupApi(object):
    def __init__(self,vh_browser):
        self.vh_browser = vh_browser
        self.cfg = self.vh_browser.cfg
        self.vh_browser.vr.get_user_group_list()

    def logout(self):
        self.vh_browser.logout()

    def group_exists(self, group_name):
        """
        If user group by this name already exists,
        return its guid. Otherwise, return None
        """
        return self.vh_browser.vr.user_group_id_from_name(group_name)

    def add_group(self, name, description='', parent_name="All Users"):
        ret_dict = {}
        # Don't bother if the group already exists...
        if self.group_exists(name):
            ret_dict['result'] = 'group_already_there'
        else:
            self.vh_browser.goto(self.cfg.user_group['EDIT_URL'])
            # get our controls...
            name_field = self.vh_browser.wait_for_element(self.cfg.user_group['TXT_GROUP_NAME'])
            desc_field = self.vh_browser.wait_for_element(self.cfg.user_group['TXT_DESCRIPTION'])
            sel_parent = Select(self.vh_browser.wait_for_element(self.cfg.user_group['SEL_PARENT_GROUP']))
            admins_only_radio = self.vh_browser.find_element_by_css(self.cfg.user_group['RB_ADMINS_ONLY'])
            save_button = self.vh_browser.wait_for_element(self.cfg.user_group['BTN_SAVE'])
            # fill in name and description...
            name_field.send_keys(name.strip()) # Remove any leading or trailing spaces
            desc_field.send_keys(description)
            # select parent group from drop-down...
            Util.select_in_dropdown_by_partial_text(sel_parent, parent_name.strip())
            # select "joinability..."
            admins_only_radio.click()
            # save ...
            save_button.click()
            # Ask self.vr to mark this name as taken...
            self.vh_browser.vr.add_temp_user_group(name, parent_name, description)
            ret_dict['result'] = 'group_successfully_added'
        return ret_dict


"""
Uses Web automation to interact with VH via
VhBrowser instance to read and write information
about landing pages.

Singleton
"""

class LandingPageApi(object):
    __instance = None
    def __new__(cls, vh_browser):
        if LandingPageApi.__instance is None:
            LandingPageApi.__instance = object.__new__(cls)
            LandingPageApi.__instance.vh_browser = vh_browser
            LandingPageApi.__instance.cfg = vh_browser.cfg
            LandingPageApi.__instance._messages = None
            LandingPageApi.__instance._pages = None
        return LandingPageApi.__instance

    def logout(self):
        self.vh_browser.logout()

    @property
    def messages(self):
        if self._messages is None:
            self.load_messages()
        return self._messages

    @property
    def pages(self):
        if self._pages is None:
            self.load_landing_page_list()
        return self._pages

    """
    If a landing page with given name already
    exists, return that page (as a dict); otherwise
    return None
    """
    def page_exists(self, page_name):
        plist = [ p for p in self.pages if p['name'].upper() == page_name.strip().upper()]
        if len(plist) == 1:
            return plist[0]
        else:
            return None

    """
    Load the landing page messages from disk files
    into RAM.
    """

    def load_messages(self):
        msg_dir = self.cfg.landing_page['MSG_STORE_DIR']
        self._messages = {}
        for k in self.cfg.landing_page_messages:
            fname = self.cfg.landing_page_messages[k]
            path_name = os.path.join(msg_dir,fname)
            with open(path_name,'r') as infile:
                # Use cfg key as message dict key, but upper-case:
                self._messages[k.upper()] = infile.read()


    """
    For each landing page, retrieve its id number, name,
    and two urls.

    The page: http://VOL_HUB_CUSTOMER.volunteerhub.com/setup/landingpages contains a table
    with id "LandingPages." Each tr in this table contains either th or td elements. For each
    row which contains td elements:
    First td contains an input tag with the "Edit" button. The tag's 'data-href' attribute
        has a URL, of which the last part (after the last '/') is the id number of the landing page.
    Second td contains a div which contains the landing page's name as its inner HTML.
    Third td contains a div which in turn contains a link -- the href of this is the URL for
        this landing page's QR code.
    Fourth td contains a div which in turn contains two links -- the href attributes
        of these links are the absolute URLs of the landing page.
    """
    def load_landing_page_list(self):
        self.vh_browser.goto(self.cfg.landing_page['LIST_URL'])
        # Wait until it's loaded before proceeding...
        self.vh_browser.wait_for_element(self.cfg.landing_page['LIST_DONE_MARKER'])
        # Locate the table containing the landing page data...
        lp_table = self.vh_browser.find_element_by_css(self.cfg.landing_page['LIST_TABLE_CSS'])
        self._pages = []
        trlist = lp_table.find_elements_by_css_selector('tr')
        # The first tr in the table is the header row, consisting
        # of th elements. The rest of them should each contain
        # four td elements, of which the first, second and fourth
        # have the info we want.
        for tr in trlist:
            tdlist = tr.find_elements_by_css_selector('td')
            if tdlist and len(tdlist) == 4:
                scratch = {}
                # In first td, page id number is at end of url...
                a = tdlist[0].find_element_by_css_selector('input')
                lpid = a.get_attribute('data-href').split('/')[-1]
                scratch['id'] = lpid
                # innerHTML of second td is the name of the page.
                d = tdlist[1].find_element_by_css_selector('div')
                inner_html = d.get_attribute('innerHTML')
                if inner_html is None:
                    inner_html = ''
                scratch['name'] = inner_html.strip()
                # Fourth td has anchor elements (probably two of them,
                # but let's not assume) containing links to the page.
                alist = tdlist[3].find_elements_by_css_selector('a')
                for i,a in enumerate(alist):
                    key = 'url' + str(i)
                    # Key is 'url0' 'url1' and so on.
                    scratch[key] = a.get_attribute('href')
                self._pages.append(scratch)



    def add_landing_page(self, org_name, team_name, page_name='', event_group='All Events'):
        self.vh_browser.goto(self.cfg.landing_page['EDIT_URL'])
        # get page elements...
        txt_page_name = self.vh_browser.wait_for_element(self.cfg.landing_page['TXT_PAGE_NAME'])
        txt_subhost  = self.vh_browser.wait_for_element(self.cfg.landing_page['TXT_SUBHOST'])
        txt_url = self.vh_browser.wait_for_element(self.cfg.landing_page['TXT_URL'])
        sel_event_group = Select(self.vh_browser.wait_for_element(self.cfg.landing_page['SEL_EVENT_GROUP']))
        sel_user_group = Select(self.vh_browser.wait_for_element(self.cfg.landing_page['SEL_USER_GROUP']))
        chk_user_group = self.vh_browser.wait_for_element(self.cfg.landing_page['CHK_USER_GROUP_FILTER'])
        chk_autojoin = self.vh_browser.wait_for_element(self.cfg.landing_page['CHK_AUTOJOIN'])
        chk_override_look = self.vh_browser.wait_for_element(self.cfg.landing_page['CHK_OVERRIDE_LOOK'])
        chk_override_msg = self.vh_browser.wait_for_element(self.cfg.landing_page['CHK_OVERRIDE_MSG'])
        btn_save_page = self.vh_browser.find_element_by_css(self.cfg.landing_page['BTN_SAVE_PAGE'])
        # Fill in some values:
        txt_page_name.clear()
        # generate page name if not passed.
        # TODO: Add logic to differentiate among "Corporate Group," "Family Group,"
        # and other parents of our parent group.
        # TODO: Add check for maximum allowable page name length.
        if page_name == '':
            page_name = 'X - ' + org_name
        txt_page_name.send_keys(page_name)
        u = Util.minify(page_name)
        txt_subhost.clear()
        txt_subhost.send_keys(u)
        txt_url.clear()
        txt_url.send_keys(u)
        # Check some boxes, select from some drop-downs:
        Util.select_in_dropdown_by_partial_text(sel_event_group, event_group)
        Util.select_in_dropdown_by_partial_text(sel_user_group, team_name)
        Util.turn_on(chk_user_group)
        Util.turn_on(chk_autojoin)
        Util.turn_off(chk_override_look)
        Util.turn_on(chk_override_msg)
        # Put in message html...
        self.insert_lp_messages(org_name, save_old_messages=False)
        # Save our work...
        btn_save_page.click()

    def insert_lp_message(self,msg_name,org_name, save_old_message):
        """
        Assumes that we're already on the editing screen for
        this landing page and that the "Override the default
        messages" has been clicked.
        """
        html_link_css = self.cfg.landing_page['LNK_' + msg_name + '_HTML']
        html_link = self.vh_browser.find_element_by_css(html_link_css)
        html_link.click()
        # Now switch to HTML Source Editor window which just popped up:
        self.vh_browser.switch_to_newest_window()
        # Wait until html source area is ready...
        source_area = self.vh_browser.wait_for_element(self.cfg.landing_page['TXT_HTML_SOURCE'])
        ## Save old contents if requsted:
        if save_old_message:
            raise Exception("Save old message not yet implemented.")
            #old_msg = source_area.get_attribute('value')
            #self.save_message(page_name, message_name, old_msg)
        source_area.clear()
        ## Prepare message...
        m = self.messages[msg_name]
        ## Don't bother if message is absent or empty:
        if m:
            m = m.replace('\t','') # html editor doesn't like tabs for some reason
            if org_name is not None:
                m = m.replace('###ORG NAME###', org_name)
            ## Now insert message into text area:
            if len(m) > 0:
                source_area.send_keys(m)
        ## Find and click 'Update' button:
        update_button = self.vh_browser.find_element_by_css(self.cfg.landing_page['BTN_SAVE_HTML'])
        update_button.click()
        ## Switch back to main window:
        self.vh_browser.return_to_previous_window()

    def insert_lp_messages(self,org_name=None, save_old_messages=False):
        for k in self.messages.keys():
            # Save breadcrumb...
            self.vh_browser.save_window_handle()
            self.insert_lp_message(k,org_name,save_old_messages)
