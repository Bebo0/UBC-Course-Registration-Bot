import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import CONFIGS

def notify_email(receiver_address, message, subject):
    """
    Sends an email from a preset address from the config file to receiver_address

    :param receiver_address: the address that will receive email
    :param message: the message of the email
    :param subject: the subject of the email
    """

    from_addr = CONFIGS.FROM_EMAIL_ADDRESS
    to_addr = receiver_address
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = subject

    body = message
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(CONFIGS.FROM_EMAIL_HOST, CONFIGS.FROM_EMAIL_PORT)
        server.starttls()
        server.login(from_addr, CONFIGS.FROM_EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(from_addr, to_addr, text)
    except smtplib.SMTPAuthenticationError as e:
        print "Unable to login to email host. Check email setting and account information."
    finally:
        if server:
            server.quit()


def generate_notification_message(pre_message, course, is_switching, is_success):
    """
    Generate a message by adding details onto pre_messaage
    :param pre_message: a String message
    :param course: a Course object
    :param is_switching: True if this is for switching section, False for registering into new course
    :param is_success: True if registration/switch was perform successfully
    :return: The final message with the necessary details
    """
    if is_switching:  # message for switching sections
        if is_success:
            pre_message += " You should now be switch into {0} from {1}.".format(course.name, course.current_registered_section)
        else:
            pre_message += " However, switching into {0} was unsuccessful. Make sure you are currently registered in a section " + \
                           "and there's no timetable conflicts.".format(course.name)

    else:  # message for registering into a course
        if is_success:
            pre_message += " You should now be registered into {0}.".format(course.name)
        else:
            pre_message += " But registration into {0} was unsuccessful. " + \
                           "Make sure you have all prerequisites and there's no timetable conflicts.".format(course.name)

    return pre_message