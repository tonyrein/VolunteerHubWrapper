#<p align="center">VolunteerHubWrapper</p>

VolunteerHub (https://www.volunteerhub.com/) is an on-line service used by non-profit agencies to help manage their volunteers’ activities. It provides a Web-based interface allowing agencies to maintain contact information, verify that waivers have been accepted, track volunteers’ hours, check people in and out of shifts, and carry out many other functions.

An organization I volunteered with in 2016 used VolunteerHub to generate “landing pages” for teams of volunteers. The page generation was done manually, taking up quite a bit of time. I wrote VolunteerHubWrapper (VHW) to automate the process.

What’s posted here is definitely not a complete application – it’s simply an illustration of some techniques that can be used to streamline use of a Web interface.

VolunteerHubWrapper uses a couple of VolunteerHub api calls; however, the VolunteerHub api did not provide all the functionality needed, so VHW uses Selenium (https://github.com/SeleniumHQ/Selenium) to control the VolunteerHub Web pages.

The library fsvhub.py is the heart of the project, the other Python files being command-line scripts which use it.

This file and other files that are part of VolunteerHubWrapper are Copyright © 2018 by Tony Rein

