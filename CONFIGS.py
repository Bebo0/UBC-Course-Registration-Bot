# set the 2 fields below to the current academic year
SEMESTER_YEAR = '2015' # 2015, 2016, etc.
SEMESTER_SEASON = 'W'  # W or S for Winter and Summer respectively

# Setting for sending email notifications:
# host and port has been set for GMail so make a new GMail account and put the address in FROM_EMAIL_ADDRESS
# and password in FROM_EMAIL_PASS then go to https://www.google.com/settings/security/lesssecureapps and check
# the "turn off" option to allow sending email updates from this app through Gmail
FROM_EMAIL_HOST = 'smtp.gmail.com'
FROM_EMAIL_PORT = 587
FROM_EMAIL_ADDRESS = 'example@gmail.com'  # put a new Gmail address here
FROM_EMAIL_PASS = 'example_password'  # put the corresponding password for the above account

# min and max between each check rotation in seconds
MIN_DELAY_BW_CHECKS = 1200
MAX_DELAY_BW_CHECKS = 1800

