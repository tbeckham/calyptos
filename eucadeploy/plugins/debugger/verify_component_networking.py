import fabric
from fabric.colors import white
from fabric.decorators import task
from fabric.operations import run, settings
from fabric.state import env
from fabric.tasks import execute
from fabric.context_managers import hide
import re
from eucadeploy.plugins.debugger.debuggerplugin import DebuggerPlugin

class VerifyComponentNetworking(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        self.info('Verify recommended NIC configuration on all hosts')
        self._confirm_nics(all_hosts)
        self.info('Verify multicast group communication between all'
                  + ' Eucalyptus java components')
        self._confirm_multicast(roles)

        return (self.passed, self.failed)

    def _confirm_nics(self, all_hosts):
        """
        Confirm if Eucalyptus components meet the following requirements:
         - at least 1 NIC
         - NIC(s) supports gigabit speeds 

        :param all_hosts: list of Eucalyptus components
        """
        # Use lspci to grab network interfaces
        lspci_output = 'lspci | egrep -i \'network|ethernet\''
        with hide('everything'):
            nic_info = self.run_command_on_hosts(lspci_output, all_hosts)

        for host in all_hosts:
            if len(nic_info[host].strip().split('\n')) >= 1:
                self.success(host + ':Component has at least one NIC'
                             + ' for a baseline deployment')
            else:
                self.failure(host + ':Component does not contain minimal' 
                             + ' number of NICs for a baseline deployment')
            
            # Check to see if all NICs support gigabit speed
            gig_nics = 0 
            for nic in nic_info[host].strip().split('\n'):
                if re.search('Gigabit (Ethernet|Network)', nic):
                    gig_nics += 1

            if len(nic_info[host].strip().split('\n')) == int(gig_nics):
                self.success(host + ':Component meets Gigabit requirement'
                             + ' for all network interfaces')
            else:
                self.failure(host + ':Component fails to meet Gigabit'
                             + ' requirement for all network interfaces')
     

    def _confirm_multicast(self, roles):                     
        """
        Test multicast communication between all Eucalyptus
        Java components.  This includes the following:
        - Cloud Controller (clc)
        - Storage Controller (storage-controller)
        - Walrus (walrus)
        - UFS (user-facing)        
 
        :param roles: set of Eucalyptus components based on roles
        """
        # Make a set of all Eucalyptus Java components
        java_components = roles['clc']
        
        euca_java_roles = ['user-facing', 'storage-controller']
        if roles['walrus']:
            euca_java_roles.append('walrus')

        for component in euca_java_roles:
            java_components.update(roles[component])

        # Install prerequisite packages for multicast test
        self._install_multicast_test_prereq(java_components)
    
        """
        While iterating through each Eucalyptus Java component,
        set one component in iperf (server mode), while 
        running iperf in client mode on other Java components.
        Once iperf has completed on each client, 
        stop the iperf server daemon on the given
        component.
        """
        for host in java_components:
            iperf_clients = []
            for element,client in enumerate(java_components):
                if client is not host:
                    iperf_clients.append(client)

            self._clear_old_logs(host) 
            iperf_cmd = ('iperf -s -u -B 228.7.7.3 -p 8773 -i 1'
                         + ' &>/tmp/test-iperf.log &')
            with hide('everything'):
                iperf_output = self.start_iperf_server(iperf_cmd,
                                                        host) 
            if not iperf_output:
                self.info('iperf (server mode) started on ' + host)
                with hide('everything'):
                    client_output = self.execute_iperf_on_hosts(iperf_clients) 
                iperf_pid_cmd = "ps | grep iperf"
                with hide('everything'):
                    iperf_pid_output = self.get_iperf_pid(iperf_pid_cmd,
                                                          host)
                iperf_pid = iperf_pid_output.strip().split()[0] 
                if client_output:
                    kill_cmd = 'kill -SIGKILL ' + iperf_pid
                    with hide('everything'):
                        kill_output = self.run_command_on_host(kill_cmd,
                                                               host)
                    if not kill_output:
                        self.success(host + ':iperf (server mode) killed'
                                     + ' successfully')
                        """
                        After successfully stopping the iperf server
                        process iperf log file and confirm clients 
                        communicated with the iperf server
                        """
                        self._process_multicast_resp(host, iperf_clients)
                    else:
                       self.failure(host + ':unable to kill iperf'
                                    + ' (server mode)')
            else:
                self.failure(host + ':iperf (server mode) failed to'
                             + ' be established')
                break

    def _process_multicast_resp(self, iperf_server, iperf_clients):

        """
        Analyze contents of iperf log on the given Eucalyptus Java
        Component, and confirm other Eucalyptus Java clients were 
        able to communicate via multicast UDP

        :param iperf_server
        :param iperf_clients
        """
        cat_cmd = 'cat /tmp/test-iperf.log'
        with hide('everything'):
            server_output = self.run_command_on_host(cat_cmd,
                                                     iperf_server)
        if server_output:
            for client in iperf_clients:
                iperf_communication = False
                for entry in server_output.strip().split('\n'):
                    if re.search(client, entry):
                        iperf_communication = True 

                if iperf_communication:
                    self.success(iperf_server + ': client '
                                 + client
                                 + ' communicated successfully'
                                 + ' for multicast membership') 
                else:
                    self.failure(iperf_server + ': client '
                                 + client + ' failed to communicate '
                                 + 'with ' + iperf_server
                                 + ' for multicast membership') 
        else:
            self.failure(iperf_server + ': Error obtaining file contents'
                         + ' of iperf log file - /tmp/test-iperf.log')

    def _clear_old_logs(self, iperf_server):
        """
        Clear old iperf log on given Eucalyptus Java component

        :param iperf_server: Client to clear old iperf log
        """
        rm_cmd = "rm -rf /tmp/test-iperf.log"
        with hide('everything'):
            rm_output = self.run_command_on_host(rm_cmd,
                                                 iperf_server)
        if not rm_output:
            self.success(iperf_server + ': old iperf log removed')
        else:
            self.failure(iperf_server + ': old iperf log failed to'
                         + ' be removed')
 
    def _install_multicast_test_prereq(self, java_components):
        """
        Install prerequisite package(s) for test to
        determine if environment allows multicast UDP connections
        between Eucalyptus Java components
 
        :param java_components: list of Eucalyptus Java components
        """
        packages = ['iperf']
        for package in packages:
            with hide('everything'):
                """
                Use rpm --query --all to confirm package
                exists; if not, issue a warning and install
                missing package
                """
                rpm_output = self.run_command_on_hosts('rpm '
                                                       + '--query --all '
                                                       + package,
                                                       java_components)
            for host in java_components:
                if re.search(package, rpm_output[host]):
                    self.success(host + ':Package found - ' + package)
                else:
                    self.warning(host + ':Package not installed - '
                                + package + '; Installing ' + package)
                    with hide('everything'):
                        yum_output = self.run_command_on_host('yum install '
                                     + ' --assumeyes --quiet --nogpgcheck ' + package,
                                     host=host)
                    if not yum_output:
                        self.success(host + ':Package installed - ' + package)
                    else:
                        self.failure(host + ':Package failed to install - ' + package)

    @task
    def iperf_command_task(user='root', password='foobar'):
        """
        Execute iperf on each host in client mode,
        testing UDP connection, binding to 228.7.7.3.
        Time-to-live is 32, port is 8773, transmitting every 3 seconds,
        and pausing 1 second between periodic bandwidth
        reports.

        :param user: username of the remote user
        :param password:  password of the remote user
        """
        env.user = user
        env.password = password
        env.parallel = True
        message = 'Running iperf (client mode) on ' + env.host
        message_style = "[{0: <20}] {1}"
        print white(message_style.format('INFO', message))
        iperf_command = ('iperf -c 228.7.7.3 -u -T 32'
                         + '-p 8773 -t 5 -i 1')
        return run(iperf_command)

    @task
    def iperf_server_command(command, user='root', password='foobar'):
        """
        Run given iperf command on specific host

        :param command: iperf command with arguments
        :param user: username of remote user
        :param password: password of remote user
        """
        env.user = user
        env.password = password
        env.parallel = True
        with settings(warn_only=True):
            return run(command, pty=False, combine_stderr=True)

    @task
    def iperf_server_pid(command, user='root', password='foobar'):
        """
        Task to discover iperf (running in server mode) PID
 
        :param command: command to obtain iperf PID
        :param user: username of remote user
        :param password: password of remote user
        """
        env.user = user
        env.password = password
        env.parallel = True
        with settings(warn_only=True):
            return run(command, pty=False, combine_stderr=True)

    def execute_iperf_on_hosts(self, hosts, host=None):
        """
        Run iperf_command_task on each host
        
        :param  hosts: list of hosts on which to execute 
                the iperf_command_task
        :param  host: single host on which to execute
                the iperf_command_task
        """
        return execute(self.iperf_command_task, hosts=hosts)

    def start_iperf_server(self, iperf_command, host):
        """
        Execute command on given host to start iperf in server
        mode
  
        :param iperf_command: iperf command with server mode flag
        :param host: host on which to start iperf in server mode
        """
        return execute(self.iperf_server_command, command=iperf_command,
                       host=host)[host]

    def get_iperf_pid(self, iperf_command, host):
        """
        Execute command to grab PID of iperf process running in
        server mode

        :param iperf_command: command to grab iperf process
        :param host: host on which to discover the iperf process
        """
        return execute(self.iperf_server_pid, command=iperf_command,
                       host=host)[host]
