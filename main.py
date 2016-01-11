import notifications
import courses_manager
import time
import random
import CONFIGS
import getpass


def go_on_standby(min_delay, max_delay, print_delay=True):
    """
    Put program to sleep for until next check; use to prevent sending too many requests
    and clogging the UBC server

    :param min_delay: delay will be greater than or equal to this in seconds
    :param max_delay: delay will be less than or equal to this in seconds
    :param print_delay: set to True to print how long till next check
    """
    rand_delay = random.randint(min_delay, max_delay)

    if print_delay:
        print "Putting program to sleep for {0} seconds".format(rand_delay)

    time.sleep(rand_delay)


if __name__ == "__main__":
    # login to account
    CWL_acc_name = raw_input("Enter CWL account name: ")
    CWL_password = getpass.getpass("Enter CWL password: ")

    courses_manager.send_login_request(CWL_acc_name, CWL_password)

    if not courses_manager.is_logged_in():
        print "Unable to login. Make sure CWL ID and password is correct."
        exit()

    # email address to provide status update
    notify_email_addr = raw_input("Enter email to receive notification: ")

    # go to proper semester
    courses_manager.go_to_semester(CONFIGS.SEMESTER_YEAR, CONFIGS.SEMESTER_SEASON)

    # add the list of course to watch
    raw_course_info = raw_input("Enter course info in the format: 'NAME, ALLOW_RESTRICTED_SEATS (T/F), MONITOR_ONLY (T/F), TO_BE_SWITCH SECTION " +
              "(empty if not switching) \n i.e CPSC 221 101, T, F or EOSC 114 101, T, F, EOSC 114 102 \n" +
              "Enter 'DONE' to finalize course list, 'REMOVE' to delete previous course from watch in case typo, VIEW to list current queue  \n").upper()

    # a buffer that will contain raw course info
    courses_for_watch = []

    # perform user command until DONE is entered
    while raw_course_info != 'DONE':
        if raw_course_info == 'REMOVE':
            if len(courses_for_watch) > 0:
                print "'" + courses_for_watch.pop() + "'" + " has been removed from queue"

        elif raw_course_info == 'VIEW':
            print "Current queue list:"
            if len(courses_for_watch) == 0:
                print "None"
            else:
                for course in courses_for_watch:
                    print course
        else:
            if raw_course_info.count(',') in (2, 3):
                courses_for_watch.append(raw_course_info)
            else:
                print "Invalid input!"

        raw_course_info = raw_input().upper()

    # convert the string in course buffer into Course objects and add them to the final course watch list
    for course in courses_for_watch:
        course_info = course.split(',')

        if len(course_info) == 3:
            courses_manager.add_course_to_watch(courses_manager.Course(course_info[0].strip(),
                                                                       course_info[1].strip() == 'T',
                                                                       course_info[2].strip() == 'T'))
        elif len(course_info) == 4:
            courses_manager.add_course_to_watch(courses_manager.Course(course_info[0].strip(),
                                                                       course_info[1].strip() == 'T',
                                                                       course_info[2].strip() == 'T',
                                                                       course_info[3].strip()))
        else:
            print "'" + course + "'" + " is invalid"

    courses_to_watch = courses_manager.get_courses_watch_list()

    # check seating status for each course in the list and perform action based on their setup
    while courses_to_watch:
        for course in courses_to_watch:
            if course.monitor_only:
                seats_info = course.get_seats_info()
                print "{0} : Total - {1}  Registered - {2} General - {3}  Restricted - {4}".format(course.name,
                                                                                                   *(seats_info[seat_type] for
                                                                                                     seat_type in
                                                                                                     seats_info)
                                                                                                   )
                continue

            status = course.get_availability_status()

            # perform action based on current seating status of course
            if status == 'No Seats':  # no seats available
                print "Couldn't find a seat for ", course.name

            elif status == "General Seats":  # general seat available
                notification_msg = "A general seat for " + course.name + " has been found!"

                # try register or switch into course
                if course.current_registered_section is None:  # register case
                    is_success = course.register_course(CWL_acc_name, CWL_password)
                    notification_msg = notifications.generate_notification_message(notification_msg, course, False, is_success)
                else:  # switch section case
                    is_success = courses_manager.switch_course_section(course.current_registered_section, course.name, CWL_acc_name, CWL_password)
                    notification_msg = notifications.generate_notification_message(notification_msg, course, True, is_success)

                courses_to_watch.remove(course)
                notifications.notify_email(notify_email_addr, notification_msg, "UBC Course Bot: " + course.name)
                print notification_msg

            elif status == "Restricted Seats":  # restricted seat available
                if course.allow_restricted_seats:
                    notification_msg = "A restricted seat for " + course.name + " has been found!"

                    # try register or switch into course
                    if course.current_registered_section is None:  # register case
                        is_success = course.register_course(CWL_acc_name, CWL_password)
                        notification_msg = notifications.generate_notification_message(notification_msg, course, False, is_success)
                    else:  # switch section case
                        is_success = courses_manager.switch_course_section(course.current_registered_section, course.name, CWL_acc_name, CWL_password)
                        notification_msg = notifications.generate_notification_message(notification_msg, course, True, is_success)

                    courses_to_watch.remove(course)
                    notifications.notify_email(notify_email_addr, notification_msg, "UBC Course Bot: " + course.name)
                    print notification_msg
                else:
                    print "Couldn't find a seat for ", course.name

            else:
                print "Error occurred when checking for seats for {0}! Double check the course name is correct!".format(course.name)
            go_on_standby(1, 10, False)

        # perform delays to avoid clogging UBC's server and avoid being flag for scripting just in case
        if courses_to_watch:
            go_on_standby(CONFIGS.MIN_DELAY_BW_CHECKS, CONFIGS.MAX_DELAY_BW_CHECKS, True)
            random.shuffle(courses_to_watch)

    raw_input("Seats for all courses has been found. Press enter to exit.")
