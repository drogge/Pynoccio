Pynoccio
========

Python interface to pinoccio API and ScoutScript commands

Pynoccio is a set of python classes which allows python programs to connect to the
Pinoccio server at https://api.pinocc.io/v1/ and execute ScoutScript commands and
Pinoccio API calls. An attempt was made to keep the python commands similar to the
ScoutScript commands they emulate. For example, to receive a report of the digital
i/o pin states in HQ you would execute the ScoutScript command pin.report.digital.
In Pynoccio you would use the command scout.pin.report.digital where scout is a
Scout object obtained from account.troops API call.

Pynoccio uses the "requests" HTTP library available at http://docs.python-requests.org/en/latest/

Three example programs are supplied to show how to use pynoccio.py:

testSS executes most of the SS commands that don't affect the networking features
of the Pinoccio. You can test the mesh and wifi network states but commands that
might cause you scout to be unable to talk are commented out.

usage: testSS [options] user password
options:

  -t <troop> troup name
  -s <scout> scout name
  
user/password is your pinocc.io login info.

<troop> specifies the name of troop you want to connect to while <scout> is the
name of a Scout in that Troop. There are some defaults built into the program that
you'll probably want to change.

execSS executes one or more ScoutScript commands. The standard command line parameters
and options are the same as in testSS.

usage: execSS [options] user password command command ...
options:

  -t <troop> troup name
  -s <scout> scout name

pin_stream executes either the pinoccio stream comman sync or stat. The only way
to exit the program is to kill it.

usage: pin_stream [options] user password [command]
options:

  -t <troop> troup name
  -s <scout> scout name
  

