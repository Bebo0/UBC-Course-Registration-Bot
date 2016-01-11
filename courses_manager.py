from urllib import urlencode
import urllib2
import cookielib
import re
import time

# region String Constants
# html patterns seat summary
TOTAL_SEAT_PATTERN = "Total Seats Remaining:</td><td align=left><strong>([0-9]+)</strong>"
CURRENTLY_REGISTERED_PATTERN = "Currently Registered:</td><td align=left><strong>([0-9]+)</strong>"
GENERAL_SEAT_PATTERN = "General Seats Remaining:</td><td align=left><strong>([0-9]+)</strong>"
RESTRICTED_SEAT_PATTERN = "Restricted Seats Remaining\*:</td><td align=left><strong>([0-9]+)</strong>"

# since the above HTML pattern will be used extensively, it makes sense to compile them into keys for better performance
TOTAL_SEAT_KEY = re.compile(TOTAL_SEAT_PATTERN)
CURRENTLY_REGISTERED_KEY = re.compile(CURRENTLY_REGISTERED_PATTERN)
GENERAL_SEAT_KEY = re.compile(GENERAL_SEAT_PATTERN)
RESTRICTED_SEAT_KEY = re.compile(RESTRICTED_SEAT_PATTERN)

# This program is designed based on Chrome's version of html output so User-Agent is set for Chrome
REQUEST_USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"

# for checking login status
LOGOUT_BUTTON_HTML = "<input type='submit' name='logout' class='btn btn-danger' value='Logout'/>"
LOGIN_STATUS_URL = "https://courses.students.ubc.ca/cs/main?submit=Login&IMGSUBMIT.x=50&IMGSUBMIT.y=13&IMGSUBMIT=IMGSUBMIT"

# HTML template for the hidden login fields
TICKET_HTML_PATTERN = '<input type="hidden" name="lt" value="(.*?)" />'
IDP_SERVICE_HTML_PATTERN = '<input type="hidden" name="IdP Service" value="(.*?)" />'
USER_HTML_PATTERN = '<input type="hidden" name="User" value="(.*?)" />'
SERVER_HTML_PATTERN = '<input type="hidden" name="Server" value="(.*?)" />'

# url template for setting school year and season
SEMESTER_URL_TEMPLATE = "https://courses.students.ubc.ca/cs/main?sessyr={}&sesscd={}"

# url template for retrieving the HTML of a course page
COURSE_URL_TEMPLATE = "https://courses.students.ubc.ca/cs/main?pname=subjarea&tname=subjareas&req=5&dept={0}&course={1}&section={2}"

# url template for registering into a course
COURSE_REGISTRATION_URL_TEMPLATE = "https://courses.students.ubc.ca/cs/main?pname=subjarea&tname=subjareas&submit=Register%20Selected&wldel={0}|{1}|{2}"
# endregion

# tracks that list of courses that needs to be monitored
courses_list = []


class Course:
    def __init__(self, name, allow_restricted_seats=True, monitor_only=False, current_registered_section=None):
        """
        :param name: the course name in string (i.e 'CPSC 221 101')
        :param allow_restricted_seats: set it to False if doesn't have access to restricted seats
        :param monitor_only: if set to True, will not perform any registering for this course, instead print course status to console
        :param current_registered_section: if already registered in a section or waitlist, set this to that section's name so a switch can be perform
        """
        self.name = name
        self.course_url = COURSE_URL_TEMPLATE.format(*(url_parameter for url_parameter in name.split()))
        self.allow_restricted_seats = allow_restricted_seats
        self.monitor_only = monitor_only
        self.current_registered_section = current_registered_section

    def get_seats_info(self):
        """
        :return: a dictionary with course info in the form:
            {
                "total seats": int,
                "current registered": int,
                "general seats": int,
                "restricted seats": int
            }
                or returns None if any 1 of the seat info is not found
        """
        response = _URL_request_helper(self.course_url, ["read", "getcode"])
        if response["getcode"] != 200:
            print "The course url does not link to a proper course page"
            return None

        page_html = response["read"]

        tot_seat_match = re.search(TOTAL_SEAT_KEY, page_html)
        cur_reg_match = re.search(CURRENTLY_REGISTERED_KEY, page_html)
        gen_seat_match = re.search(GENERAL_SEAT_KEY, page_html)
        res_seat_match = re.search(RESTRICTED_SEAT_KEY, page_html)

        if tot_seat_match and cur_reg_match and gen_seat_match and res_seat_match:
            seats_info = {
                "total seats": int(tot_seat_match.group(1)),
                "current registered": int(cur_reg_match.group(1)),
                "general seats": int(gen_seat_match.group(1)),
                "restricted seats": int(res_seat_match.group(1))
            }
            return seats_info
        else:
            return None

    def get_availability_status(self):
        """
        Return the availability status in text. Would like to do this with enums but Python 2.7
        doesn't support enum.

        :return: a string representing a course's status:
            Unable to get seating info -> "Failed to get seating info"
            No seats available -> "No Seats"
            General seat found -> "General Seats"
            Restricted seat found -> "Restricted Seats"
            None of the above -> "Inconsistent seating info detected"
        """
        seats_info = self.get_seats_info()

        if not seats_info:
            return "Failed to get seating info"
        # no seats available
        if seats_info["total seats"] == 0:
            return "No Seats"
        # general seats available
        elif seats_info["general seats"] != 0:
            return "General Seats"
        # restricted seats available
        elif seats_info["restricted seats"] != 0:
            return "Restricted Seats"
        # error while attempting to get seat info
        else:
            return "Inconsistent seating info detected"

    def register_course(self, username, password):
        """
        :param username: CWL account name
        :param password: CWL account password
        :return: True if registration was successful, false othterwise
        """
        if not is_logged_in():
            send_login_request(username, password)

        # need to fix below
        course_info = self.name.split()
        register_url = COURSE_REGISTRATION_URL_TEMPLATE.format(course_info[0], course_info[1], course_info[2])

        response = _URL_request_helper(register_url, ["getcode"])

        if response['getcode'] == 200:
            return True
        else:
            return False


def add_course_to_watch(course):
    """
    Add a course to watch list if there doesn't already exist in the list
    :param course: a Course object
    """
    if course not in courses_list:
        courses_list.append(course)

def remove_course_from_watch(course):
    """
    Remove a course to watch list and catch exception if its not found
    :param course: a Course object
    """
    if course not in courses_list:
        try:
            courses_list.remove(course)
        except ValueError:
            print "Course doesn't exist in watch list. Check for logic errors in adding course to watch list."


def get_courses_watch_list():
    """
    :return: The course watch list
    """
    return courses_list


def _install_cookie_opener():
    """
    Installs cookie opener for cookie handling, which is required for the login procedure
    """
    cookie_jar = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    opener.addheaders = [('User-agent', REQUEST_USER_AGENT)]
    urllib2.install_opener(opener)


def send_login_request(user_id, password):
    """
    Sends a post request with the required authentication fields to login user so tasks like course registration and
    section switching can be perform

    :param user_id: CWL account user ID
    :param password: CWL account password
    """
    login_url1 = "https://cas.id.ubc.ca/ubc-cas/login/"

    # cookie handler is required for all activities that requires authentication
    if urllib2._opener is None:
        _install_cookie_opener()

    response = _URL_request_helper(login_url1, ["read", "info"])
    resp_html = response["read"]
    resp_info = response["info"]

    ticket = re.search(TICKET_HTML_PATTERN, resp_html)
    idp_service = re.search(IDP_SERVICE_HTML_PATTERN, resp_html)
    user_ip = re.search(USER_HTML_PATTERN, resp_html)
    server = re.search(SERVER_HTML_PATTERN, resp_html)

    # get JSESSIONID from the response header
    jsession_html = "Set-Cookie: JSESSIONID=(.*?);"
    jsession_val = re.search(jsession_html, str(resp_info))

    # Second request form data with ticket
    login_form_data = {
        'username': user_id,
        'password': password,
        'execution': 'e1s1',
        '_eventId': 'submit',
        'lt': ticket.group(1),
        'submit': 'Continue >',
        'IdP Service': idp_service.group(1),
        'User': user_ip.group(1),
        'Server': server.group(1)
    }

    # login URL with JSESSIONID
    login_url2 = "https://cas.id.ubc.ca/ubc-cas/login;jsessionid=" + jsession_val.group(1)

    _URL_request_helper(login_url2, [], login_form_data)

    # log into the course section of Student Service; courses can be added or switched after this process
    course_service_login_url = "https://courses.students.ubc.ca/cs/secure/login"
    urllib2.urlopen(course_service_login_url)


def go_to_semester(year, season):
    """
    Sets the proper semester so the correct course directory is in effect. Should be done after login.

    :param year: the school year as a string i.e 2015
    :param season: the season (W or S)
    """
    target_semester_url = SEMESTER_URL_TEMPLATE.format(year, season)

    response = _URL_request_helper(target_semester_url, ["getcode"])

    if response["getcode"] == 200:
        print "Active semester: {} {}".format(year, season)
    else:
        print "Invalid semester year or season. Will use default semester instead"


def switch_course_section(original_section, new_section, CWL_acc, CWL_pass):
    """
    Switch a currently registered course into a new section

    :param original_section: a string of the section currently registered in (i.e CPSC221 L1A)
    :param new_section: a string of the section to be switch into (i.e CPSC221 L1B)
    :return: True if the switch was successful, false otherwise
    """
    if not is_logged_in():
        send_login_request(CWL_acc, CWL_pass)

    original_section_id = original_section.name.split()
    new_section_id = new_section.name.split()

    course_switch_url = "https://courses.students.ubc.ca/cs/main?pname=regi_sections&tname=regi_sections"
    course_switch_url2 = "https://courses.students.ubc.ca/cs/main"

    initial_form_data = {
        'pname': 'switch',
        'tname': 'switch',
        'wldel': original_section_id[0] + '|' + original_section_id[1] + '|' + original_section_id[2],
        'submit': 'Switch Selected Section'
    }

    # initialize switch request
    _URL_request_helper(course_switch_url, [], initial_form_data)

    final_form_data = {
        'pname': 'regi_sections',
        'tname': 'regi_sections',
        'switchFromKey': original_section_id[0] + '|' + original_section_id[1] + '|' + original_section_id[2],
        'switchtype': 'sect',
        'wldel': new_section_id[0] + '|' + new_section_id[1] + '|' + new_section_id[2],
        'submit': 'Switch Sections'
    }

    finalize_switch_request = _URL_request_helper(course_switch_url2, ['getcode'], final_form_data)

    if finalize_switch_request['getcode'] == 200:
        return True
    else:
        return False


def is_logged_in():
    """
    Checks whether the user is log in or not. Current implementation relies on detecting whether the logout button exists
    in the response html.

    :return: true if user is already logged in, false otherwise
    """
    page_html = _URL_request_helper(LOGIN_STATUS_URL, ['read'])['read']

    if page_html.find(LOGOUT_BUTTON_HTML) != -1:
        return True
    else:
        return False


def _URL_request_helper(request_url, attributes=[], form_data=None):
    """
    Makes GET or POST request depending on whether form_data is set and returns a dictionary of
    attributes with their corresponding data return by the request or None if an error has occurred;
    If a network error occur either at the client or server side, this function will retry with the request
    until it succeeds

    :param request_url: the URL to send the request
    :param attributes: a list of attributes to obtain from the response object (read, info, geturl or getcode)
    :param form_data: an unencoded dictionary of form data if making a POST request
    :return: a dictionary of with all the attributes specified by the attributes parameter or empty dict if no attributes
    was specified
    """
    while True:
        try:
            if form_data is None:
                response = urllib2.urlopen(request_url)
            else:
                request = urllib2.Request(request_url, urlencode(form_data))
                response = urllib2.urlopen(request)

            response_data = {}
            for attribute in attributes:
                response_data[attribute] = getattr(response, attribute)()
            return response_data

        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                print "Unable to reach {}".format(request_url)
                print "Reason: ", e.reason
            elif hasattr(e, 'code'):
                print "The server couldn't fulfill the request for {}".format(request_url)
                print "Error code: ", e.code

            print "Retrying in 60 seconds"
            time.sleep(60)
            continue

