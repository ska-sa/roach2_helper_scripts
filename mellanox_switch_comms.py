#!/usr/bin/python
'''
This class allows you to run commands on a remote host and provide
input if necessary.

VERSION 1.2
'''
import paramiko
import logging
import socket
import time
import datetime
import re


# ================================================================
# class MySSH
# ================================================================
class MySSH:
    '''
    Create an SSH connection to a server and execute commands.
    Here is a typical usage:

        ssh = MySSH()
        ssh.connect('host', 'user', 'password', port=22)
        if ssh.connected() is False:
            sys.exit('Connection failed')

        # Run a command that does not require input.
        status, output = ssh.run('uname -a')
        print 'status = %d' % (status)
        print 'output (%d):' % (len(output))
        print '%s' % (output)

        # Run a command that does requires input.
        status, output = ssh.run('sudo uname -a', 'sudo-password')
        print 'status = %d' % (status)
        print 'output (%d):' % (len(output))
        print '%s' % (output)
    '''
    def __init__(self, logger, compress=True):
        '''
        @param compress  Enable/disable compression.
        '''
        self.ssh = None
        self.transport = None
        self.compress = compress
        self.bufsize = 65536

        self.info = logger.info
        self.debug = logger.debug
        self.error = logger.error

    def __del__(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None

    def connect(self, hostname, username, password, port=22):
        '''
        Connect to the host.

        @param hostname  The hostname.
        @param username  The username.
        @param password  The password.
        @param port      The port (default=22).

        @returns True if the connection succeeded or false otherwise.
        '''
        self.debug('connecting %s@%s:%d' % (username, hostname, port))
        self.hostname = hostname
        self.username = username
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(hostname=hostname,
                             port=port,
                             username=username,
                             password=password)
            self.transport = self.ssh.get_transport()
            self.transport.use_compression(self.compress)
            self.info('succeeded: %s@%s:%d' % (username,
                                               hostname,
                                               port))
        except socket.error as e:
            self.transport = None
            self.error('failed: %s@%s:%d: %s' % (username,
                                                 hostname,
                                                 port,
                                                 str(e)))
        except paramiko.BadAuthenticationType as e:
            self.transport = None
            self.error('failed: %s@%s:%d: %s' % (username,
                                                 hostname,
                                                 port,
                                                 str(e)))

        return self.transport is not None

    def run(self, cmd, input_data=' ', timeout=10):
        '''
        Run a command with optional input data.

        Here is an example that shows how to run commands with no input:

            ssh = MySSH()
            ssh.connect('host', 'user', 'password')
            status, output = ssh.run('uname -a')
            status, output = ssh.run('uptime')

        Here is an example that shows how to run commands that require input:

            ssh = MySSH()
            ssh.connect('host', 'user', 'password')
            status, output = ssh.run('sudo uname -a', '<sudo-password>')

        @param cmd         The command to run.
        @param input_data  The input data (default is None).
        @param timeout     The timeout in seconds (default is 10 seconds).
        @returns The status and the output (stdout and stderr combined).
        '''
        self.debug('running command: (%d) %s' % (timeout, cmd))

        if self.transport is None:
            self.error('no connection to %s@%s:%s' % (str(self.username),
                                                      str(self.hostname),
                                                      str(self.port)))
            return -1, 'ERROR: connection not established\n'

        # Fix the input data.
        input_data = self._run_fix_input_data(input_data)

        # Initialize the session.
        self.debug('initializing the session')
        session = self.transport.open_session()
        session.set_combine_stderr(True)
        session.get_pty()#height=1000)
        #session.exec_command(cmd)
        session.invoke_shell()
        session.send(cmd)
        session.send('\n')
        output,status = self._run_poll(session, timeout, input_data)
        #status = session.recv_exit_status()
        self.debug('output size %d' % (len(output)))
        self.debug('status %d' % (status))
        return status, output

    def connected(self):
        '''
        Am I connected to a host?

        @returns True if connected or false otherwise.
        '''
        return self.transport is not None

    def _run_fix_input_data(self, input_data):
        '''
        Fix the input data supplied by the user for a command.

        @param input_data  The input data (default is None).
        @returns the fixed input data.
        '''
        if input_data is not None:
            if len(input_data) > 0:
                if '\\n' in input_data:
                    # Convert \n in the input into new lines.
                    lines = input_data.split('\\n')
                    input_data = '\n'.join(lines)
            return input_data.split('\n')
        return []

    def _run_send_input(self, session, stdin, input_data):
        '''
        Send the input data.

        @param session     The session.
        @param stdin       The stdin stream for the session.
        @param input_data  The input data (default is None).
        '''
        if input_data is not None:
            #self.info('session.exit_status_ready() %s' % str(session.exit_status_ready()))
            self.error('stdin.channel.closed %s' % str(stdin.channel.closed))
            if stdin.channel.closed is False:
                self.debug('sending input data')
                stdin.write(input_data)

    def _run_poll(self, session, timeout, input_data, prompt=[' > ',' # ']):
        '''
        Poll until the command completes.

        @param session     The session.
        @param timeout     The timeout in seconds.
        @param input_data  The input data.
        @returns the output
        '''
        def check_for_prompt(output,prompt):
            for prmt in prompt:
                # Only check last 3 characters in return string
                if output[-3:].find(prmt) > -1:
                    return True
            return False    

        interval = 0.1
        maxseconds = timeout
        maxcount = maxseconds / interval

        # Poll until completion or timeout
        # Note that we cannot directly use the stdout file descriptor
        # because it stalls at 64K bytes (65536).
        input_idx = 0
        timeout_flag = False
        self.debug('polling (%d, %d)' % (maxseconds, maxcount))
        start = datetime.datetime.now()
        start_secs = time.mktime(start.timetuple())
        output = ''
        session.setblocking(0)
        status = -1
        while True:
            if session.recv_ready():
                data = session.recv(self.bufsize)
                self.debug(repr(data))
                output += data
                self.debug('read %d bytes, total %d' % (len(data), len(output)))

                if session.send_ready():
                    # We received a potential prompt.
                    # In the future this could be made to work more like
                    # pexpect with pattern matching.

                    #If 'lines 1-45' found in ouput, send space to the pty 
                    #to trigger the next page of output. This is needed if 
                    #more that 24 lines are sent (default pty height)
                    pattern = re.compile('lines \d+-\d+')

                    if re.search(pattern, output):
                        session.send(' ')
                    elif input_idx < len(input_data):
                        data = input_data[input_idx] + '\n'
                        input_idx += 1
                        self.debug('sending input data %d' % (len(data)))
                        session.send(data)

            #exit_status_ready signal not sent when using 'invoke_shell'
            #self.info('session.exit_status_ready() = %s' % (str(session.exit_status_ready())))
            #if session.exit_status_ready():
            if check_for_prompt(output,prompt) == True:
                status = 0
                break

            # Timeout check
            now = datetime.datetime.now()
            now_secs = time.mktime(now.timetuple()) 
            et_secs = now_secs - start_secs
            self.debug('timeout check %d %d' % (et_secs, maxseconds))
            if et_secs > maxseconds:
                self.debug('polling finished - timeout')
                timeout_flag = True
                break
            time.sleep(0.200)

        self.debug('polling loop ended')
        if session.recv_ready():
            data = session.recv(self.bufsize)
            output += data
            self.debug('read %d bytes, total %d' % (len(data), len(output)))

        self.debug('polling finished - %d output bytes' % (len(output)))
        if timeout_flag:
            self.debug('appending timeout message')
            output += '\nERROR: timeout after %d seconds\n' % (timeout)
            session.close()

        return output, status


# ================================================================
# MAIN
# ================================================================
if __name__ == '__main__':
    import sys,os,re,string
    from optparse import OptionParser
    import ConfigParser
    from multiprocessing.pool import ThreadPool

    desc = """This programs connects to Mellanox switches via SSH and runs commands.
             The output is written to a file. The hosts and commands can be passed
             via command line or listed in a config file, command line overrides
             config file if config file is specified. If no output filename is
             specified the executed command and a timestamp will be used as the output
             filename. If more than one command is listed on the command line or
             in the config file and an output filename is specified only the last
             result will be saved."""
    parser = OptionParser(description=desc)
    parser.set_usage('%prog [options]')
    parser.add_option('-r', '--run_command', type=str, default=None,
                      help='Command to run, command/s to be placed in quotes and comma seperated')
    parser.add_option('-e', dest='enable', action='store_true',
                      help='Put switch in enable mode. Overrides config file setting.')
    parser.add_option('-n', dest='hostnames', type=str, default=None,
                      help='Comma seperated list of hosts')
    parser.add_option('-l', dest='loglevel', type=str, default=None,
                      help='Log level: DEBUG,INFO,ERROR,WARINING,FATAL. Default = INFO')
    parser.add_option('-c', '--config_file', type=str, default=None,
                      help=("""File containing list of hosts and list of commands.
                             File syntax example:
                             [config]                        
                             enable=False                         
                             commands = 
                                 show interface ethernet status
                                 show configuration
                             hosts = 
                                 cbfsw-s3.cbf.mkat.karoo.kat.ac.za
                                 cbfsw-s4.cbf.mkat.karoo.kat.ac.za
                                 cbfsw-s5.cbf.mkat.karoo.kat.ac.za
                             loglevel = ERROR
                             """))
    parser.add_option('-o', '--out', type=str, default=None,
                      help='Output filename.')
    loglevel = 'INFO'
    enable = False
    hosts = None
    cmds = None
    opts, args = parser.parse_args()
    def parse_lines(value):
        ret = filter(None, [x.strip() for x in value.splitlines()])
        if ret:
            ret = filter(None, [x if x[0] != '#' else None for x in ret])
        return ret

    if opts.config_file:
        if os.path.isfile(opts.config_file):
            config = ConfigParser.ConfigParser()
            config.read(opts.config_file)
            try:
                cmds = parse_lines(config.get('config','commands'))
                hosts =  parse_lines(config.get('config','hosts'))
                loglevel = config.get('config','loglevel')
                enable = config.getboolean('config','enable')
            except Exception as e:
                print 'Exception occured: {}'.format(e)
                parser.error('Config file syntax incorrect')
        else:
            parser.error('Specified file does not exist.')

    if opts.hostnames:
        hosts = opts.hostnames.split(',')
        print hosts
    if opts.run_command:
        cmds = opts.run_command.split(',')
        print cmds
    if opts.enable:
        enable=True
    if opts.loglevel:
        loglevel=opts.loglevel

    if not cmds or not hosts:
        parser.error('Specified command or hosts using commandline or a config file.')

    # Setup the logger
    logger = logging.getLogger('mellanox_switch_comms')
    level = logging.getLevelName(loglevel)
    logger.setLevel(level)
    fmt = '%(asctime)s %(funcName)s:%(lineno)d %(message)s'
    date_fmt = '%Y-%m-%d %H:%M:%S'
    logging_format = logging.Formatter(fmt, date_fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(logging_format)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    port = 22
    username = 'admin'
    password = 'admin'
    sudo_password = password  # assume that it is the same password

    def ssh_conn(hostname):
        ssh = MySSH(logger)
        ssh.connect(hostname=hostname,
                    username=username,
                    password=password,
                    port=port)
        if ssh.connected() is False:
            print 'ERROR: connection failed.'
            sys.exit(1)
        return ssh
    
    def rem_extra_chars(in_str):
        pat = re.compile('lines \d+-\d+ ')
        in_str = re.sub(pat, '', in_str)
        pat = re.compile('lines \d+-\d+\/\d+ \(END\) ')
        in_str = re.sub(pat, '', in_str)
        return in_str.replace('\r','')

    def run_cmd(ssh_obj, cmd, indata=None, enable=False):
        '''
        Run a command with optional input.

        @param cmd    The command to execute.
        @param indata The input data.
        @returns The command exit status and output.
                 Stdout and stderr are combined.
        '''

        prn_cmd = cmd
        cmd = 'terminal type dumb\n'+cmd
        if enable:
            cmd = 'enable\n'+cmd
        output = ''
        output += ('\n'+'='*64 + '\n')
        output += ('host    : ' + ssh_obj.hostname + '\n')
        output += ('command : ' + prn_cmd + '\n')
        status, outp = ssh_obj.run(cmd, indata, timeout=30)
        output += ('status  : %d' % (status) + '\n')
        output += ('output  : %d bytes' % (len(output)) + '\n')
        output += ('='*64 + '\n')
        outp = rem_extra_chars(outp)
        output += outp
        return output

    ssh_list = [0]*len(hosts)
    thread_obj = [0]*len(hosts)
    pool = ThreadPool(processes=len(hosts))
    for i,host in enumerate(hosts):
        print host
        thread_obj[i] = pool.apply_async(ssh_conn, args=(host,))
    for i,host in enumerate(hosts):
        ssh_list[i] = thread_obj[i].get()

    print ('SSH connections established')
    ret = [0]*len(hosts)
    for cmd in cmds:

        timestr = time.strftime("%Y_%m_%d-%H_%M")
        if opts.out:
            outf = open(opts.out, "w")
        else:
            pattern = re.compile('[\W_]+') 
            cmd_name = pattern.sub('_', cmd) 
            outf = open("{}_{}.txt".format(cmd_name, timestr), "w")
        
        for i,ssh_obj in enumerate(ssh_list):
            thread_obj[i] = pool.apply_async(run_cmd, args=(ssh_obj,cmd), kwds={'enable':'enable'})
        for i,ssh_obj in enumerate(ssh_list):
            ret[i] = thread_obj[i].get()
        for val in ret:
            outf.write(val)
            print val
        outf.close()

    print ('Closing SSH connections')
    for i,ssh_obj in enumerate(ssh_list):
        thread_obj[i] = pool.apply_async(ssh_obj.ssh.close)


