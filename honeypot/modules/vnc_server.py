__G__ = "(G)bd249ce4"

from twisted.internet.protocol import Protocol,Factory
from twisted.internet import reactor
from psutil import process_iter
from signal import SIGTERM
from time import sleep
from multiprocessing import Process
from Crypto.Cipher import DES
from binascii import unhexlify
from logging import DEBUG, Handler, WARNING, getLogger,basicConfig

class QVNCServer():
	def __init__(self,ip=None,port=None,username=None,password=None,mocking=False,dict_=None,logs=None):
		self.ip= ip or '0.0.0.0'
		self.port = port or 5900
		self.username = username or "test"
		self.password = password or "test"
		self.mocking = mocking or None
		self.random_servers = ['VNC Server']
		self.file_name = dict_ or None
		self.challenge = unhexlify("00000000901234567890123456789012")
		if not dict_:
			self.words = ["test"]
		else:
			self.load_words()
		self.setup_logger(logs)

	def setup_logger(self,logs):
		self.logs = getLogger("chameleonlogger")
		self.logs.setLevel(DEBUG)
		if logs:
			from custom_logging import CustomHandler
			self.logs.addHandler(CustomHandler(logs))
		else:
			basicConfig()

	def load_words(self,):
		with open(self.file_name, 'r') as file:
			self.words = file.read().splitlines()

	def decode(self,c, r):
		try:
			for word in self.words:
				temp = word
				word = word.strip('\n').ljust(8, '\00')[:8]
				rev_word = []
				for i in xrange(0,8):
					rev_word.append(chr(int('{:08b}'.format(ord(word[i]))[::-1], 2)))
				output = DES.new(''.join(rev_word),DES.MODE_ECB).encrypt(c)
				#output = des(rev_word).encrypt(c)
				if output == r:
					return temp
		except Exception:
			pass

		return None

	def vnc_server_main(self):
		_q_s = self

		class CustomVNCProtocol(Protocol):

			_state = None

			def connectionMade(self):
				self.transport.write('RFB 003.008\n')
				self._state = 1

			def dataReceived(self, data):
				if self._state == 1:
					if data == 'RFB 003.008\n':
						self._state = 2
						self.transport.write(unhexlify('0102'))
				elif self._state == 2:
					if data == unhexlify('02'):
						self._state = 3
						self.transport.write(_q_s.challenge)
				elif self._state == 3:
					_x = _q_s.decode(_q_s.challenge,unhexlify(''.join(hex(ord(c))[2:] for c in data)))
					if _x:
						if _x == _q_s.password:
									_q_s.logs.info(["servers",{'server':'vnc_server','action':'login','status':'success','ip':self.transport.getPeer().host,'port':self.transport.getPeer().port,'username':'UnKnown','password':_q_s.password}])
						else:
							_q_s.logs.info(["servers",{'server':'vnc_server','action':'login','status':'failed','ip':self.transport.getPeer().host,'port':self.transport.getPeer().port,'username':'UnKnown','password':_x}])
					else:
						if len(data) == 16:
							#we need to check the lenth check length first
							_q_s.logs.info(["servers",{'server':'vnc_server','action':'login','status':'failed','ip':self.transport.getPeer().host,'port':self.transport.getPeer().port,'username':'UnKnown','password':''.join(hex(ord(c))[2:] for c in data)}])
					self.transport.loseConnection()
				else:
					self.transport.loseConnection()

			def connectionLost(self, reason):
				self._state = None

		factory = Factory()
		factory.protocol = CustomVNCProtocol
		reactor.listenTCP(port=self.port, factory=factory, interface=self.ip)
		reactor.run()

	def run_server(self,process=False):
		self.close_port()
		if process:
			self.vnc_server = Process(name='QVNCServer_', target=self.vnc_server_main)
			self.vnc_server.start()
		else:
			self.vnc_server_main()

	def kill_server(self,process=False):
		self.close_port()
		if process:
			self.vnc_server.terminate()
			self.vnc_server.join()

	def test_server(self,ip,port,username,password):
		sleep(3)
		try:
			ip or self.ip
			port or self.port 
			username or self.username
			password or self.password
		except Exception:
			pass

	def close_port(self):
		for process in process_iter():
			try:
				for conn in process.connections(kind='inet'):
					if self.port == conn.laddr.port:
						process.send_signal(SIGTERM)
						process.kill()
			except:
				pass

if __name__ == "__main__":
	from server_options import server_arguments
	parsed = server_arguments()

	if parsed.docker or parsed.aws or parsed.custom:
		QVNCServer = QVNCServer(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password,mocking=parsed.mocking,logs=parsed.logs)
		QVNCServer.run_server()

	if parsed.test:
		QVNCServer = QVNCServer(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password,mocking=parsed.mocking,logs=parsed.logs)
		QVNCServer.test_server(ip=parsed.ip,port=parsed.port,username=parsed.username,password=parsed.password)