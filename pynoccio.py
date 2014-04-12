import sys
import datetime
import requests
import json

_api_url = 'https://api.pinocc.io/v1/'

_account = None # Don't like this but we want to be able look up troop and
		# scout stuff

""" Set debug level """
_pinoccio_debug = 0
def set_debug(v):
    global _pinoccio_debug
    _pinoccio_debug = v

verbose_ids = True
def set_verbose_ids(vids):
    verbose_ids = vids

def scout_name(tid, sid):
    if not verbose_ids:
    	return "%d-%d" % (tid, sid)
    t = _account.troop(tid)
    s_name = t.scout(sid).name
    return s_name

def print_dict(d):
    for k in d.keys():
        print k+':', d[k]

""" Convert millis since the Linux epoch to str """
def _time_str(millis):
    return datetime.datetime.fromtimestamp(millis/1000.).strftime("%Y/%m/%d-%H:%M:%S.%f")

def _delta_str(millis):
    return "%.4f" % (millis/1000.)

"""
Sometimes we don't get a valid reply to some report commands. They should
contain a json string but end up empty. Try to detect those and print the
bogus value.
"""
def make_json(t):
    try:
	return json.loads(t)
    except Exception as e:
	print e
	print 'text: "%s"' % t
	raise

""" Create an object from a ScoutScript command json result. The main thing
that people will be interested in here is reply. """
class SSreply(object):
    """
    These fields are common with SSerror
    u'type': u'reply',
    u'id': u'1mai126'
    u'from': 1,
    u'commandsPending': 0,
    u'basetime': 99,
    u'reply': u'409\r\n',
    u'tid': u'2',
    u'_cid': 9,
    u'messagesQueued': 0,

    This field is unique with SSreply
    u'end': True,
    """
    def __init__(self, d):
        super(SSreply, self).__init__()
        self.raw = d
	self.error = False
	try:
	    self.type = str(self.raw['type'])
	    self.id = str(self.raw['id'])
	    self.scout = int(self.raw['from'])
	    self.commandsPending = int(self.raw['commandsPending'])
	    self.basetime = self.raw['basetime']
	    self.reply = self.raw['reply']
	    self.tid = self.raw['tid']
	    self._cid = self.raw['_cid']
	    self.messagesQueued = self.raw['messagesQueued']
	except KeyError:
	    print >>sys.stderr, 'invalid SS reply: "%s"' % str(d)
	    raise
	try:
	    self.end = self.raw['end']
	except:
	    pass

        # for some reason replies have \r\n in them. remove it now
        r = self.reply.replace('\r', '').strip()
	# Convert strings of digits into ints
	try:
	    ir = int(r)
	except:
	    # Convert unicode into str
	    if isinstance(r, unicode):
	    	r = str(r)
	    ir = r
        self.reply = ir

    def __str__(self):
        s =  'id: '+str(self.id)
        s += ', scout: '+str(self.scout)
        s += ', pending: '+str(self.commandsPending)
        s += ', queued: '+str(self.messagesQueued)
        s += ', basetime: '+str(self.basetime)
        s += ', tid: '+str(self.tid)
        s += ', _cid: '+str(self._cid)
        s += ', end: '+str(self.end)
        s += ', reply: '
	# If the command didn't return anything, print none
        if self.reply == "":
            s += "none"
        else:
            s += '"""\n'+str(self.reply)+'\n"""'
        return s

""" Create an object from a ScoutScript command json error result. """
class SSerror(SSreply):
    def __init__(self, status_code, d):
        super(SSerror, self).__init__(d)
        """
         These fields are common with SSreply
         u'type': u'reply',
         u'id': u'ooq1641',
         u'from': u'1',
         u'account': u'1024',
         u'commandsPending': 0,
         u'basetime': 10000,
         u'reply': u''}
         u'tid': u'2',
         u'_cid': 42,
         u'messagesQueued': 0,

         These fields fields are unique to errors. There could be more
         fields for different types of errors

         u'err': u'base timeout in 10000 ms',
         u'timeerror': True,    
         u'timeout': 10000,
         u'command': u'power.ischargingp',
        """
	if _pinoccio_debug > 1:
	    print self.raw
        self.status_code = status_code
	self.error = True
	try:
	    self.err = str(self.raw['err'])
	    self.command = str(self.raw['command'])
	    self.timeerror = self.raw.get('timeerror', False)
	    if self.timeerror:
		self.timeout = self.raw['timeout']
	    else:
		self.timeout = -1
	except KeyError:
	    print >>sys.stderr, 'invalid SS reply: "%s"' % str(d)

    def __str__(self):
        s =  'id: '+str(self.id)
        s += ', scout: '+str(self.scout)
        s += ', pending: '+str(self.commandsPending)
        s += ', queued: '+str(self.messagesQueued)
        s += ', basetime: '+str(self.basetime)
        s += ', tid: '+str(self.tid)
        s += ', _cid: '+str(self._cid)
        s += ', error: '+str(self.err)
        try:
            s += ', command: '+str(self.command)
        except:
            pass
        s += ', reply: '
        if self.reply == "":
            s += "none"
        else:
            s += '"""\n'+str(self.reply)+'\n"""'
        return s

class announcement:
    """ {u'type': u'announce',
         u'report': [1, u'hello'],
         } """
    def __init__(self, d):
	self.group = int(d['report'][0])
    	self.message = str(d['report'][1])

    def __str__(self):
    	return 'group: %d, message: %s' % (self.group, self.message)

class availabilityState:
    """ {u'type': u'available',
	 u'scout': 1,
	 u'available': 1,
         u'_t': 1396156657710.001,
         } """
    def __init__(self, d):
    	self.scout = int(d['scout'])
    	self.available = int(d['available'])

    def __str__(self):
    	return 'scout: %d, available: %d' % (self.scout, self.available)

class backpacksState():
    """ {u'type': u'backpacks'
         u'list': [],}"""
    def __init__(self, d):
        self.backpacks = d['list']

    def __str__(self):
        return 'backpacks: '+str(self.backpacks)

class connectionState:
    def __init__(self, d):
	self.status = d['status']
	self.ip = d.get('ip', "")

    def __str__(self):
	return 'status: %s, ip: %s' % (str(self.status), str(self.ip))

class ledState:
    """ {u'type': u'led'
         u'led': [0, 0, 0],
         u'torch': [0, 255, 0],},"""
    def __init__(self, d):
	self.led = d["led"]
	self.torch = d["torch"]

    def __str__(self):
	return 'led: %s, torch: %s' % (self.led, self.torch)

class meshState:
    """ {u'type': u'mesh',
         u'scoutid': 2,
         u'troopid': 2,
         u'power': u'3.5 dBm',
         u'rate': u'250 kb/s',
         u'routes': 0,
         u'channel': 20}"""
    def __init__(self, d):
	self.scoutid = int(d["scoutid"])
	self.troopid = int(d["troopid"])
	self.routes = d["routes"]
	self.channel = int(d["channel"])
	self.rate = str(d["rate"])
	self.power = str(d["power"])

    def __str__(self):
	return 'scout: %d-%d, routes: %d channel: %d rate: %s power: %s' % \
	    (self.troopid, self.scoutid, self.routes,
	     self.channel, self.rate, self.power)

class nameState:
    def __init__(self, name):
    	self.name = str(name)

    def __str__(self):
    	return 'name: %s' % (self.name)

class pinState:
    """ {u'type': u'analog|digital',
         u'state': [-1, -1, -1, -1, -1, -1, -1, -1],
         u'mode': [-1, -1, -1, -1, -1, -1, -1, -1]}"""
    def __init__(self, d):
	self.pin_type = d['type']
	self.mode = d["mode"]
	self.state = d["state"]

    def __str__(self):
	mode_strs = {-2: 'RES', -1: 'DIS', 0: 'IN', 1: 'OUT', 2: 'PUP'}
	dp_vals = {-1: 'DIS', 0: 'LOW', 1: 'HI'}

	s = '%s mode: [' % self.pin_type
	pin_count = 7 if self.pin_type == 'digital' else 8
	sep = ''
	for pin in range(0, pin_count):
	    s += sep+mode_strs[self.mode[pin]]
	    sep = ' '
	s += '], value: ['
	sep = ''
	if self.pin_type == 'digital':
	    for pin in range(0, pin_count):
		s += sep+dp_vals[self.state[pin]]
		sep = ' '
	else:
	    for pin in range(0, pin_count):
		if self.state[pin] == -1:
		    vs = dp_vals[-1]
		else:
		    vs = '  '+str(self.state[pin])
		s += sep+vs
		sep = ' '
	s += ']'
	return s

class powerState:
    """ {u'type': u'power',
         u'battery': 90,
         u'voltage': 403,
         u'vcc': True,
         u'charging': False},"""
    def __init__(self, d):
	self.battery = d['battery']
	self.voltage = d['voltage']
	self.charging = d['charging']
	self.vcc = d['vcc']

    def __str__(self):
	return 'battery: %d%%, voltage: %4.02f, charging: %s vcc: %s' % \
	    (self.battery, self.voltage/100., self.charging, self.vcc)

# Scout commands
class scoutState:
    """ {u'type': u'scout'
         u'lead': False,
         u'family': 1000,
         u'hardware': 1,
         u'version': 1,
         u'build': 2014032001,
         u'serial': 2000612,}"""
    def __init__(self, d):
	self.lead = d['lead']
	self.version = d['version']
	self.hardware = d['hardware']
	self.family = d['family']
	self.serial = d['serial']
	self.build = d['build']

    def __str__(self):
	s = 'lead: '+str(self.lead)
	s += ', version: '+str(self.version)
	s += ', hardware: '+str(self.hardware)
	s += ', family: '+str(self.family)
	s += ', serial: '+str(self.serial)
	s += ', build: '+str(self.build)
	return s

class freeState:
    def __init__(self, s):
	"""0790 17261 17096 : used/free/large"""
	vs = s.split()
	self.used = int(vs[0])
	self.free = int(vs[1])
	self.large = int(vs[2])

    def __str__(self):
	return "used: %d free: %d large: %d" % (self.used, self.free, self.large)

class tempState:
    """ {u'type': u'temp',
         u'current': 26,
         u'high': 27,
         u'low': 25}, """
    def __init__(self, d):
	self.current = d['current']
	self.high = d['high']
	self.low = d['low']

    def __str__(self):
	return 'current: %d, high: %d low: %d' % \
	    (self.current, self.high, self.low)

class uptimeState:
    """ {u'type': u'uptime'
         u'reset': u'Power-on',
         u'random': 16807,
         u'millis': 1045,
         u'free': 18610,}, """
    def __init__(self, d):
	self.reset = str(d['reset'])
	self.random = int(d['random'])
	self.millis = int(d['millis'])
	self.free = int(d['free'])

    def __str__(self):
        return 'reset: %s, random: %s, free: %s, uptime: %s' % \
	    (self.reset, self.random, self.free, _delta_str(self.millis))

class wifiState:
    def __init__(self, d):
	self.connected = d['connected']
	self.hq = d['hq']

    def __str__(self):
	s = 'connected: '+str(self.connected)
	s += ', hq: '+str(self.hq)
	return s

"""
Class for converting output of stats and sync commands from json
to something more directly usable by pyhon. """
class State(object):

    def __init__(self, d):
        super(State, self).__init__()
        self.raw = d
        self.type = str(d['type'])
        self.troop = int(d.get('troop', 0))
	self.scout = int(d.get('scout', 0))
        self.time = int(d.get('time', 0))
        self.value = d.get('value', {})
	self.valid = True

        if self.type == 'power':
            self.state_data = powerState(self.value)
        elif self.type == 'temp':
            self.state_data = tempState(self.value)
        elif self.type == 'uptime':
            self.state_data = uptimeState(self.value)
        elif self.type == 'scout':
            self.state_data = scoutState(self.value)
        elif self.type == 'backpacks':
            self.state_data = backpacksState(self.value)
	elif self.type in ['digital', 'analog']:
            self.state_data = pinState(self.value)
        elif self.type == 'mesh':
            self.state_data = meshState(self.value)
        elif self.type == 'led':
            self.state_data = ledState(self.value)
	elif self.type == 'connection':
            self.state_data = connectionState(self.value)
	elif self.type == 'name':
            self.state_data = nameState(self.value)
	elif self.type == 'available':
            self.state_data = availabilityState(self.value)
	elif self.type == 'announce':
            self.state_data = announcement(self.value)
	elif self.type == 'wifi':
	    self.state_data = wifiState(self.value)
	elif self.type in ['data', 'token']:
	    self.valid = False
        else:
	    print d
            raise Exception
 
    def __str__(self):
        s = 'type: '+self.type
	if self.type in ['connection', 'name']:
	    s += ', troop: '+str(self.troop)
	else:
	    s += ', scout: '+scout_name(self.troop, self.scout)
	if self.type != 'name':	# for some reason the name state doesn't get a time stamp
	    s +=', time: '+_time_str(self.time)
	s += ', '+str(self.state_data)
	return s

class SSCmd(object):
    def __init__(self, scout):
        super(SSCmd, self).__init__()
        self.scout = scout

    def run(self, cmd):
	return self.scout.run(cmd)

class PowerCmd(SSCmd):
    def __init__(self, scout):
        super(PowerCmd, self).__init__(scout)

    @property
    def ischarging(self):
        return self.run('print power.ischarging')

    @property
    def percent(self):
        return self.run('print power.percent')

    @property
    def voltage(self):
        return self.run('print power.voltage')

    @property
    def enablevcc(self):
        return self.run('print power.enablevcc')

    @property
    def disablevcc(self):
        return self.run('print power.disablevcc')

    def sleep(self, millis):
        return self.run('print power.sleep(%d)' % (millis))

    @property
    def report(self):
        res = self.run('power.report')
        # convert json string reply to power report object
	if not res.error:
	    res.reply = powerState(make_json(res.reply))
	return res

class MeshCmd(SSCmd):
    def __init__(self, scout):
        super(MeshCmd, self).__init__(scout)

    def config(self, scoutId, troopId, channel=20):
        return self.run('print mesh.config(%d, %d, %d)' % (scoutId, troopId, channel))

    def setpower(self, powerLevel):
        return self.run('print mesh.setpower(%d)' % (powerLevel))

    def setdatarate(self, dataRate):
        return self.run('print mesh.setdatarate(%d)' % (dataRate))

    @property
    def getkey(self):
        return self.run('print mesh.getkey')

    def key(self, key):
        return self.run('print mesh.key("%s")' % (key))

    @property
    def resetkey(self):
        return self.run('print mesh.resetkey')

    def joingroup(self, group):
        return self.run('print mesh.joingroup(%d)' % (group))

    def leavegroup(self, group):
        return self.run('print mesh.leavegroup(%d)' % (group))

    def ingroup(self, group):
        return self.run('print mesh.ingroup(%d)' % (group))

    def send(self, scoutId, message):
        return self.run('print mesh.send(%d, "%s")' % (scoutId, message))

    def verbose(self, v):
    	return self.run('print mesh.verbose(%d)' % v)

    @property
    def report(self):
        res = self.run('mesh.report')
        # convert json string reply to mesh report object
	if not res.error:
	    res.reply = meshState(make_json(res.reply))
	return res

    @property
    def routing(self):
        return self.run('print mesh.routing')

    def announce(self, groupId, message):
        return self.run('print mesh.announce(%d, "%s")' % (groupId, message))

    @property
    def signal(self):
        return self.run('print mesh.signal')

    @property
    def loss(self):
        return self.run('print mesh.loss')

class MiscCmd(SSCmd):
    def __init__(self, scout):
        super(MiscCmd, self).__init__(scout)

    @property
    def temperature(self):
        return self.run('print temperature')

    @property
    def randomnumber(self):
        return self.run('print randomnumber')

    @property
    def lastreset(self):
        return self.run('lastreset')

    @property
    def uptime(self):
        return self.run('uptime')

    @property
    def report(self):
        return self.run('report')

    def verbose(self, v):
    	return self.run('print verbose(%d)' % v)

class LedCmd(SSCmd):
    def __init__(self, scout):
        super(LedCmd, self).__init__(scout)

    def blink(self, r, g, b, ms=500):
        return self.run('print led.blink(%d, %d, %d, %d)' % (r, g, b, ms))

    @property
    def off(self):
        return self.run('print led.off')

    def display(self, color, ms=None, cont=None):
	cmd = 'print led.'+color
	if ms is not None:
	    cmd += '(%d' % ms
	    if cont is not None:
		cmd += ',%d' % cont
	    cmd += ')'
        return self.run(cmd)

    def torch(self, ms=None, cont=None):
	cmd = 'print led.torch'
	if ms is not None:
	    cmd += '(%d' % ms
	    if cont is not None:
		cmd += ',%d' % cont
	    cmd += ')'
        return self.run(cmd)

    def on(self, ms=None, cont=None):
	return self.torch(ms, cont)

    def sethex(self, hexval):
        return self.run('print led.sethex("%s")' % (hexval))

    @property
    def gethex(self):
        return self.run('print led.gethex')

    def setrgb(self, r, g, b):
        return self.run('print led.setrgb(%d, %d, %d)' % (r, g, b))

    @property
    def isoff(self):
    	return self.run('print led.isoff')

    def savetorch(self, r, g, b):
        return self.run('print led.savetorch(%d, %d, %d)' % (r, g, b))

    @property
    def report(self):
        res = self.run('led.report')
        # convert json string reply to led report object
	if not res.error:
	    res.reply = ledState(make_json(res.reply))
	return res

class PinCmd(SSCmd):
    dPinNames = ['d2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8']
    aPinNames = ['a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']

    class PinReportCmd:
        def __init__(self, cmd):
            self.cmd = cmd

        @property
        def digital(self):
            res = self.cmd.run('pin.report.digital')
	    # convert json string reply to pin report object
	    if not res.error:
		res.reply = pinState(make_json(res.reply))
	    return res

        @property
        def analog(self):
            res = self.cmd.run('pin.report.analog')
	    # convert json string reply to pin report object
	    if not res.error:
		res.reply = pinState(make_json(res.reply))
	    return res

    def __init__(self, scout):
        super(PinCmd, self).__init__(scout)
        self.report = PinCmd.PinReportCmd(self)

    # Pin commands
    def makeinput(self, pin):
        return self.run('print pin.makeinput("%s")' % pin)

    def makeinputup(self, pin):
        return self.run('print pin.makeinputup("%s")' % pin)

    def makeoutput(self, pin):
        return self.run('print pin.makeoutput("%s")' % pin)

    def disable(self, pin):
        return self.run('print pin.disable("%s")' % pin)

    def setmode(self, pin, mode):
        return self.run('print pin.setmode("%s", %s)' % (pin, mode))

    def read(self, pin):
        return self.run('print pin.read("%s")' % pin)

    def write(self, pin, value):
        return self.run('print pin.makeinput("%s", %s)' % (pin, value))

    def save(self, pin, mode, value=None):
	cmd = 'pin.save("%s", %s' % (pin, mode)
	if value is not None:
	    cmd += ', %s' % value
	cmd += ')'
        return self.run(cmd)

    def report(self):
        return self.report

class BackpackCmd(SSCmd):
    def __init__(self, scout):
        super(BackpackCmd, self).__init__(scout)

    @property
    def report(self):
        res = self.run('backpack.report')
	print res
        # convert json string reply to led report object
	#if not res.error:
	#    res.reply = ledState(make_json(res.reply))
	return res

    @property
    def list(self):
        return self.run('backpack.list')

    def eeprom(self, bpid):
	return self.run('backpack.eeprom(%d)' % bpid)

    #print >>sys.stderr, scout.backpack.eeprom.update.reply
    def detail(self, bpid):
	return self.run('print backpack.detail(%d)' % bpid)

    def resources(self, bpid):
	return self.run('print backpack.resources(%d)' % bpid)

class ScoutCmd(SSCmd):
    def __init__(self, scout):
        super(ScoutCmd, self).__init__(scout)

    @property
    def report(self):
	res = self.run('scout.report')
	# convert json string reply to scout report object
	if not res.error:
	    res.reply = scoutState(make_json(res.reply))
	return res

    @property
    def isleadscout(self):
        return self.run('print scout.isleadscout')

    def delay(self, ms):
        return self.run('print scout.delay(%d)' % ms)

    @property
    def free(self):
	res = self.run('scout.free')
	# convert string reply to free state object
	if not res.error:
	    res.reply = freeState(res.reply)
	return res

    @property
    def daisy(self):
        return self.run('print scout.daisy');

    @property
    def boot(self):
        return self.run('print scout.boot');

    @property
    def otaboot(self):
        return self.run('print scout.otaboot');

class HQCmd(SSCmd):
    def __init__(self, scout):
        super(HQCmd, self).__init__(scout)

    # HQ commands
    def settoken(self, token):
    	return self.run('print hq.settoken("%s") % token')

    @property
    def gettoken(self):
    	return self.run('hq.gettoken')

    def verbose(self, v):
    	return self.run('print hq.verbose(%d)' % v)

    def _print(self, msg):
    	return self.run('print hq.print("%s")' % msg)

class EventsCmd(SSCmd):
    def __init__(self, scout):
        super(EventsCmd, self).__init__(scout)

    # Event commands
    @property
    def start(self):
    	return self.run('print events.start')

    @property
    def stop(self):
    	return self.run('print events.stop')

    def setcycle(self, digitalMs, analogMs, peripheralMs):
    	return self.run('print events.setcycle(%d, %d, %d)' %
			(digitalMs, analogMs, peripheralMs))

    def verbose(self, v):
    	return self.run('print hq.verbose(%d)' % v)

class KeyCmd(SSCmd):
    def __init__(self, scout):
        super(KeyCmd, self).__init__(scout)

    def key(self, key):
	return self.run('print key("%s")' % key)

    def _print(self, id):
	return self.run('print key.print(%d)' % id)

    def number(self, id):
	return self.run('print key.number(%d)' % id)

    def save(self, key, v):
	return self.run('print key.save(:"%s", %d)' % (key, v))

class WifiCmd(SSCmd):
    def __init__(self, scout):
        super(WifiCmd, self).__init__(scout)

    # Wifi commands
    #`{"type":"wifi","version":0,"connected":true,"hq":true}
    @property
    def report(self):
	res = self.run('wifi.report')
	# convert json string reply to wifi report object
	if not res.error:
	    res.reply = wifiState(make_json(res.reply))
	return res

    @property
    def list(self):
    	return self.run('wifi.list')

    @property
    def dhcp(self, host):
    	return self.run('print wifi.dhcp("%s")' % host)

    @property
    def static(self, ip, netmask, gateway, dns):
    	return self.run('print wifi.static("%s", "%s", "%s", "%s")' %
		   (ip, netmask, gateway, dns))

    @property
    def reassociate(self):
    	return self.run('print wifi.reassociate')

    @property
    def command(self, command):
    	return self.run('print wifi.command("%s")' % command)

    @property
    def gettime(self):
    	return self.run('wifi.gettime')

    def verbose(self, v):
    	return self.run('print wifi.verbose(%d)' % v)

    def stats(self, stype):
    	return self.status(stype)

    def status(self, stype):
    	return self.run('wifi.status(%d)' % stype)

class Scout(object):
    def __init__(self, parent, troop, id, time, updated, name):
        object.__init__(self)
        self.parent = parent
        self.troop = troop
        self.id = id
        self.time = time
        self.updated = updated
        self.name = name

        self._powerCmd = PowerCmd(self)
        self._meshCmd = MeshCmd(self)
        self._miscCmd = MiscCmd(self)
        self._ledCmd = LedCmd(self)
        self._pinCmd = PinCmd(self)
        self._backpackCmd = BackpackCmd(self)
	self._scoutCmd = ScoutCmd(self)
	self._hqCmd = HQCmd(self)
	self._eventsCmd = EventsCmd(self)
	self._keyCmd = KeyCmd(self)
	self._wifiCmd = WifiCmd(self)

    @property
    def power(self):
        return self._powerCmd

    @property
    def mesh(self):
        return self._meshCmd

    @property
    def misc(self):
        return self._miscCmd

    @property
    def led(self):
        return self._ledCmd

    @property
    def pin(self):
        return self._pinCmd

    @property
    def backpack(self):
        return self._backpackCmd

    @property
    def scout(self):
    	return self._scoutCmd

    @property
    def hq(self):
    	return self._hqCmd

    @property
    def events(self):
    	return self._eventsCmd

    @property
    def key(self):
    	return self._keyCmd

    @property
    def wifi(self):
    	return self._wifiCmd

    def run(self, cmd):
	if _pinoccio_debug:
	    print >>sys.stderr, cmd
        r = requests.post(_api_url+str(self.troop)+'/'+str(self.id)+'/command',
                          data={'command':cmd, 'token':self.parent.token})
        if r.status_code == 200:
            if _pinoccio_debug > 1:
                print >>sys.stderr, r.text
            return SSreply(r.json()['data'])
	return SSerror(r.status_code, r.json()['data'])

    @property
    def banner(self):
        return self.run('banner');

    def stats(self, report):
        r = requests.get(_api_url+'stats',
                         data={'token':self.parent.token,'report':report,
                               'scout':self.id,'troop':self.troop},
                         stream=True)
        if r.status_code == 200:
            buf = ''
            for chunk in r.iter_content(1):
                if chunk[0] == '\n':
                    state = State(make_json(buf)['data'])
		    if state.valid:
			yield(state)
                    buf = ''
                else:
                    buf += chunk[0]
        else:
            print_dict(r.json()['data'])

    def __str__(self):
        return str(self.troop)+'-'+str(self.id)+' "'+self.name+'" '+str(self.time)+' '+str(self.updated)

class Troop(object):
    def __init__(self, parent, account, name, token, online, id):
        object.__init__(self)
        self.parent = parent
        self.id = id
        self.account = account
        self.name = name
        self.token = token
        self.online = online
        self.scouts = []

        self.load_scouts()

    def make_scout(self, s):
        return Scout(self.parent, self.id, s['id'], s['time'], s['updated'], s['name'])

    def load_scouts(self):
        self.scouts = []
        r = requests.get(_api_url+str(self.id)+'/scouts', data={'token':self.parent.token})
        if r.status_code == 200:
            for s in r.json()['data']:
                self.scouts.append(self.make_scout(s))
            return
        print_dict(r.json()['data'])

    def scout(self, id):
        for s in self.scouts:
            if ((isinstance(id, basestring) and s.name == id) or
                s.id == id):
                return s
        return None

    def __str__(self):
        return str(self.id)+' "'+self.name+'" '+str(self.account)+' '+self.token+' '+str(self.online)

class Account(object):
    def __init__(self, user=None, password=None, no_load=False):
        object.__init__(self)
	global _account
	_account = self
        self.account = None
        self.token = None
        self.troops = []
        if user is not None:
            self.login(user, password, no_load=no_load)

    def login(self, user, password, no_load=False):
        r = requests.post(_api_url+'login',
                          data={'password':password,'user':user})
        if r.status_code == 200:
            j = r.json()['data']
            self.token = j['token']
            self.account = j['account']
            if not no_load:
                self.load_troops()
        else:
            print_dict(r.json()['data'])

    def account_info(self):
        r = requests.get(_api_url+'account', data={'token':self.token})
        if r.status_code == 200:
            return r.json()['data']
        print_dict(r.json()['data'])
        return None
    
    def make_Troop(self, t):
        return Troop(self, t['account'], t['name'], t['token'], t['online'], t['id'])

    def load_troops(self):
        """ Get a list of all the troops associated with the pinoccio account. """
        self.troops = [] # No Troops for you!
        r = requests.get(_api_url+'troops', data={'token':self.token})
        if r.status_code == 200:
            for t in r.json()['data']:
                self.troops.append(self.make_Troop(t))
            return
        print_dict(r.json()['data'])

    def troop(self, id):
        for t in self.troops:
            if ((isinstance(id, basestring) and t.name == id) or
                t.id == id):
                return t
        return None

    def sync(self):
        r = requests.get(_api_url+'sync', data={'token':self.token}, stream=True)
        buf = ""
        if r.status_code == 200:
            for chunk in r.iter_content(1):
                if chunk[0] == '\n':
		    if _pinoccio_debug > 1:
		    	print >>sys.stderr, buf
                    state = State(json.loads(buf)['data'])
		    if state.valid:
                        yield(state)
                    buf = ""
                else:
                    buf += chunk[0]
        else:
            print_dict(r.json()['data'])

