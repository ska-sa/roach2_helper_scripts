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
    def __init__(self, compress=True, loglevel='ERROR'):
        '''
        Setup the initial verbosity level and the logger.

        @param compress  Enable/disable compression.
        @param verbose   Enable/disable verbose messages.
        '''
        self.ssh = None
        self.transport = None
        self.compress = compress
        self.bufsize = 65536

        # Setup the logger
        self.logger = logging.getLogger('MySSH')
        level = logging.getLevelName(loglevel)
        self.logger.setLevel(level)

        fmt = '%(asctime)s MySSH:%(funcName)s:%(lineno)d %(message)s'
        format = logging.Formatter(fmt)
        handler = logging.StreamHandler()
        handler.setFormatter(format)
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        self.info = self.logger.info

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
        self.info('connecting %s@%s:%d' % (username, hostname, port))
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
            self.info('failed: %s@%s:%d: %s' % (username,
                                                hostname,
                                                port,
                                                str(e)))
        except paramiko.BadAuthenticationType as e:
            self.transport = None
            self.info('failed: %s@%s:%d: %s' % (username,
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
        self.info('running command: (%d) %s' % (timeout, cmd))

        if self.transport is None:
            self.info('no connection to %s@%s:%s' % (str(self.username),
                                                     str(self.hostname),
                                                     str(self.port)))
            return -1, 'ERROR: connection not established\n'

        # Fix the input data.
        input_data = self._run_fix_input_data(input_data)

        # Initialize the session.
        self.info('initializing the session')
        session = self.transport.open_session()
        session.set_combine_stderr(True)
        session.get_pty()#height=1000)
        #session.exec_command(cmd)
        session.invoke_shell()
        session.send(cmd)
        session.send('\n')
        output,status = self._run_poll(session, timeout, input_data)
        #status = session.recv_exit_status()
        self.info('output size %d' % (len(output)))
        self.info('status %d' % (status))
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
            self.info('stdin.channel.closed %s' % str(stdin.channel.closed))
            if stdin.channel.closed is False:
                self.info('sending input data')
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
        self.info('polling (%d, %d)' % (maxseconds, maxcount))
        start = datetime.datetime.now()
        start_secs = time.mktime(start.timetuple())
        output = ''
        session.setblocking(0)
        status = -1
        while True:
            if session.recv_ready():
                data = session.recv(self.bufsize)
                self.info(repr(data))
                output += data
                self.info('read %d bytes, total %d' % (len(data), len(output)))

                if session.send_ready():
                    # We received a potential prompt.
                    # In the future this could be made to work more like
                    # pexpect with pattern matching.

                    #If highligted 'lines' found in ouput, send space to the pty 
                    #to trigger the next page of output. This is needed if 
                    #more that 24 lines are sent (default pty height)
                    if repr(output).find('x1b[7mlines ') > -1:
                        session.send(' ')
                    elif input_idx < len(input_data):
                        data = input_data[input_idx] + '\n'
                        input_idx += 1
                        self.info('sending input data %d' % (len(data)))
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
            self.info('timeout check %d %d' % (et_secs, maxseconds))
            if et_secs > maxseconds:
                self.info('polling finished - timeout')
                timeout_flag = True
                break
            time.sleep(0.200)

        self.info('polling loop ended')
        if session.recv_ready():
            data = session.recv(self.bufsize)
            output += data
            self.info('read %d bytes, total %d' % (len(data), len(output)))

        self.info('polling finished - %d output bytes' % (len(output)))
        if timeout_flag:
            self.info('appending timeout message')
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


    desc = """This programs connects to Mellanox switches via SSH and runs commands.
             The output is written to a file. The hosts and commands can be passed
             via command line or listed in a config file, command line overrides
             config file if config file is specified. If no output filename is
             specified the executed command and a timestamp will be used as the output
             filename."""
    parser = OptionParser(description=desc)
    parser.set_usage('%prog [options]')
    parser.add_option('-r', '--run_command', type=str, default=None,
                      help='Command to run, command/s to be placed in quotes and comma seperated')
    parser.add_option('-e', dest='enable', action='store_true',
                      help='Put switch in enable mode. Overrides config file setting.')
    parser.add_option('-n', dest='hostnames', type=str, default=None,
                      help='Comma seperated list of hosts')
    parser.add_option('-l', dest='loglevel', type=str, default='ERROR',
                      help='Log level: DEBUG,INFO,ERROR,WARINING,FATAL. Default = ERROR')
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
    loglevel = 'ERROR'
    enable = False
    hosts = None
    cmds = None
    opts, args = parser.parse_args()
    def parse_lines(value):
        return filter(None, [x.strip() for x in value.splitlines()])

    if opts.hostnames:
        hosts = opts.hostnames.split(',')
    if opts.run_command:
        cmds = opts.run_command.split(',')
    if opts.enable:
        enable=True
    if opts.config_file:
        if os.path.isfile(opts.config_file):
            config = ConfigParser.ConfigParser()
            config.read(opts.config_file)
            try:
                if not cmds: 
                    cmds = parse_lines(config.get('config','commands'))
                if not hosts:
                    hosts =  parse_lines(config.get('config','hosts'))
                loglevel = config.get('config','loglevel')
                if not enable:
                    enable = config.getboolean('config','enable')
            except NoOptionError:
                parser.error('Config file syntax incorrect')
        else:
            parser.error('Specified file does not exist.')

    if not cmds or not hosts:
        parser.error('Specified command or hosts using commandline or a config file.')

    port = 22
    username = 'admin'
    password = 'admin'
    sudo_password = password  # assume that it is the same password
    
    def ssh_conn(hostname):
        # Create the SSH connection
        ssh = MySSH(loglevel=loglevel)
        ssh.connect(hostname=hostname,
                    username=username,
                    password=password,
                    port=port)
        if ssh.connected() is False:
            print 'ERROR: connection failed.'
            sys.exit(1)
        return ssh

    def rem_esc_seq(in_str):
        strt_idx = 0
        end_idx = 1
        esc_seq = '\x1b'
        while (strt_idx != -1) and (end_idx != -1):
            strt_idx = in_str.find(esc_seq)
            end_idx = in_str.find(esc_seq, strt_idx+1)+3
            if strt_idx >= end_idx:
                break
            else:
                in_str = in_str[:strt_idx] + in_str[end_idx:]
        return in_str.replace('\r','')

    def run_cmd(ssh_list, cmd, indata=None, enable=False, filename=None):
        '''
        Run a command with optional input.

        @param cmd    The command to execute.
        @param indata The input data.
        @returns The command exit status and output.
                 Stdout and stderr are combined.
        '''
        timestr = time.strftime("%Y_%m_%d-%H_%M")
        if filename:
            outf = open(filename, "w")
        else:
            pattern = re.compile('[\W_]+') 
            cmd_name = pattern.sub('_', cmd) 
            outf = open("{}_{}.txt".format(cmd_name, timestr), "w")
        
        prn_cmd = cmd
        if enable:
            cmd = 'enable\n'+cmd

        for ssh_obj in ssh_list:
            outf.write('\n'+'='*64 + '\n')
            outf.write('host    : ' + ssh_obj.hostname + '\n')
            outf.write('command : ' + prn_cmd + '\n')
            status, output = ssh_obj.run(cmd, indata, timeout=30)
            outf.write('status  : %d' % (status) + '\n')
            outf.write('output  : %d bytes' % (len(output)) + '\n')
            outf.write('='*64 + '\n')
            fixed_out = rem_esc_seq(output)
            outf.write('{}'.format(fixed_out))
            print fixed_out
        outf.close()

    ssh_list = []
    for host in hosts:
        ssh_list.append(ssh_conn(host))

    for cmd in cmds:
        run_cmd(ssh_list,cmd, enable=enable, filename=opts.out)

    for ssh_obj in ssh_list:
        ssh_obj.ssh.close()

