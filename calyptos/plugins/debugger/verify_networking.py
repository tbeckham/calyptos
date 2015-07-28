import fabric
from fabric.colors import white
from fabric.decorators import task
from fabric.operations import run, settings, local
from fabric.state import env
from fabric.tasks import execute
from fabric.context_managers import hide
import re
from calyptos.plugins.debugger.debuggerplugin import DebuggerPlugin

class VerifyConnectivity(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        self._install_conn_tool(all_hosts)
        self._verify_enduser_access(roles['user-facing'])
        self._verify_storage_controller_comms(roles)
        self._verify_osg_communication(roles)
        self._verify_java_db_comms(roles)
        self._verify_clc_cc_comms(roles)
        self._verify_cc_nc_comms(roles)


        return (self.passed, self.failed)

    def _install_conn_tool(self, all_hosts):
        """
        Install iperf on all components in order to
        perform network connectivity tests.

        :param all_hosts: set of all Eucalyptus components
        """
        self.info('Confirm iperf has been installed on'
                  + ' all components')
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
                                                       all_hosts)
            for host in all_hosts:
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

    def _verify_enduser_access(self, end_user_service_pts):
        """
        Verify end-user access to particular Eucalyptus Java
        components for user-facing service APIs.
  
        :param  end_user_service_pts: a set of Eucalyptus
                                      Java components
        """
        self.info('Verify End-User Connectivity to User Facing'
                  + ' Services and Cloud Controller')
        ports = ['8773']
        for host in end_user_service_pts:
            for port in ports:
                end_pt = host + ":" + port
                with hide('everything'):
                    access_result = self.test_service_port(end_pt)
                for output in access_result.strip().split('\n'):
                    if re.search('HTTP/1.1 404', access_result):
                        self.success(host + ':End-User access available on port '
                                     + port)
                    else:
                        self.failure(host + ':End-User unavailable on port '
                                     + port)

    def _verify_storage_controller_comms(self, roles):
        """
        Verify User Facing Service(s), Node Controller and
        Storage Controller(s) can communicate to
        to the Storage Controller(s) on TCP port 8773.

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        self.info('Verify Eucalyptus Component communication'
                  + ' to the Storage Controller')
        java_hosts = roles['clc']
        java_hosts = java_hosts.union(roles['storage-controller'])

        for sc in roles['storage-controller']:
            iperf_cmd = 'iperf -c ' + sc + ' -T 32 -t 3 -i 1 -p 8773'
            self.info('Verifying all Eucalyptus Java Components are'
                      + ' able to communicate with Storage Controller'
                      + ' ' + sc + ' on TCP port 8773') 
            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           java_hosts)    
            self._process_output(iperf_result,
                                 java_hosts,
                                 component='Eucalyptus Java Component', 
                                 test_component=sc,
                                 port='8773')

            ncs = {}
            for name in roles['cluster']:
                if sc in roles['cluster'][name]:
                    ncs = roles['node-controller'].intersection(
                                                                roles['cluster'][name])
            
            self.info('Verifying Node Controllers associated with the same'
                      + ' cluster as the Storage Controller ' + sc
                      + ' can communicate on TCP port 8773')   

            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           ncs)    
            self._process_output(iperf_result,
                                 ncs,
                                 component='Node Controller', 
                                 test_component=sc,
                                 port='8773')

                
    def _verify_osg_communication(self, roles):
        """
        Confirm proper communication between Cloud Controller,
        Node Controller(s), and Storage Controller(s) to Object
        Storage Gateway.

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        self.info('Verify Eucalyptus Component communication'
                  + ' to the Object Storage Gateway')
        components = roles['clc']
        for role in ['storage-controller', 'node-controller']:
            components = components.union(roles[role])

        for osg in roles['user-facing']:
            iperf_cmd = 'iperf -c ' + osg + ' -T 32 -t 3 -i 1 -p 8773'
            self.info('Verifying Cloud Controller, Node Controller(s) and'
                      + ' and Storage Controller(s) are able to communicate'
                      + ' with Object Storage Gateway ' + osg + ' on TCP port 8773') 
            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           components)    

            self._process_output(iperf_result,
                                 components,
                                 component='Eucalyptus Component', 
                                 test_component=osg,
                                 port='8773')

        
    def _verify_java_db_comms(self, roles):
        """
        Verify Eucalyptus Java components can communicate to 
        the database running on the Cloud Controller on 
        TCP port 8777

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        self.info('Confirm Eucalyptus Java components'
                  + ' can communicate with database on'
                  + ' Cloud Controller component')
        java_components = roles['user-facing']

        euca_java_roles = ['storage-controller']
        if roles['walrus']:
            euca_java_roles.append('walrus')

        for component in euca_java_roles:
            java_components = java_components.union(roles[component])

        for host in roles['clc']:
            iperf_cmd = 'iperf -c ' + host + ' -T 32 -t 5 -i 1 -p 8777'
            self.info('Verifying Eucalyptus Java Components'
                      + ' are able to communicate'
                      + ' with Cloud Controller ' + host + ' on TCP port 8777') 
            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           java_components)    

            self._process_output(iperf_result,
                                 java_components,
                                 component='Eucalyptus Java Component', 
                                 test_component=host,
                                 port='8777')


    def _verify_clc_cc_comms(self, roles):
        """
        Verify Cloud Controller(s) can communicate to 
        Cluster Controller on TCP port 8774 

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        self.info('Verify proper connectivity between'
                  + ' Cloud Controller and Cluster'
                  + ' Controller(s)')
        for host in roles['cluster-controller']:
            iperf_cmd = 'iperf -c ' + host + ' -T 32 -t 5 -i 1 -p 8774'
            self.info('Verifying Cloud Controller'
                      + ' is able to communcate'
                      + ' with Cluster Controller ' + host + ' on TCP port 8774') 
            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           roles['clc'])    

            self._process_output(iperf_result,
                                 roles['clc'],
                                 component='Cloud Controller', 
                                 test_component=host,
                                 port='8774')

            
    def _verify_cc_nc_comms(self, roles):        
        """
        Verify Cluster Controller(s) can communicate to 
        Node Controller(s) on TCP port 8775 - based upon cluster
        association 

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        self.info('Verify proper connectivity between'
                  + ' Cluster Controller(s) and Node'
                  + ' Controller(s)')
        for cluster in roles['cluster']:
            cluster_ctrlr = roles['cluster'][cluster].intersection(
                                                                roles[
                                                                'cluster-controller'
                                                                ])
            cc_list = list(cluster_ctrlr)
            cc = ', '.join(str(element) for element in cc_list)
            nodes = roles['cluster'][cluster].intersection(roles[
                                                        'node-controller'
                                                        ])
           
            self.info('Verifying Cluster Controller '
                      + cc
                      + ' in cluster ' + cluster
                      + ' can communicate to Node Controller(s)'
                      + ' on TCP port 8775')
            for node in nodes:
                iperf_cmd = ('iperf -c ' + node 
                             + ' -T 32 -t 3 -i 1 -p 8775')
                with hide('everything'):
                    iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                               cluster_ctrlr)    
                self._process_output(iperf_result,
                                     cluster_ctrlr,
                                     component='Cluster Controller', 
                                     test_component=node,
                                     port='8775')
            

    def _process_output(self, iperf_result, hosts, component, test_component, port):
        """
        Process iperf output from host(s)

        :param iperf_result: list of iperf output for host(s)
        :param hosts: host(s) that returned output from iperf test command
        :param component: type of component associated with hosts
        :param test_component: Eucalyptus component which hosts were tested against
                               in the iperf test command
        :param port: port used in iperf test command 
        """
        for host in hosts:
            flag = False
            for output in iperf_result[host].strip().split('\n'):
                if re.search('Connection refused', output):
                    flag = True

            if flag:
                self.failure(host + ':' + component + ' was'
                             + ' not able to connect to '
                             + test_component + ' on TCP port ' + port)
            else:
                self.success(host + ':' + component
                             + ' successfully connected to '
                             + test_component + ' on TCP port ' + port)

    @task
    def iperf_command_task(command, user='root', password='foobar'):
        """
        Execute iperf on each host in client mode

        :param command:  Iperf command to execute
        :param user: username of the remote user
        :param password:  password of the remote user
        """
        env.user = user
        env.password = password
        env.parallel = True
        message = 'Running iperf test on ' + env.host
        message_style = "[{0: <20}] {1}"
        print white(message_style.format('INFO', message))
        return run(command)

    @task
    def test_service_port(host):
        """
        Use curl to test access to Cloud Controller and
        User facing services. 
        
        :param host: host to execute test against to
                     confirm end-user client access
        """
        return local("curl -I --connect-timeout 5 " + host, capture=True)

    def execute_iperf_on_hosts(self, iperf_test, hosts, host=None):
        """
        Run iperf_command_task on each host

        :param  iperf_test: specific iperf client test to execute
                            on each host
        :param  hosts: list of hosts on which to execute
                the iperf_command_task
        :param  host: single host on which to execute
                the iperf_command_task
        """
        return execute(self.iperf_command_task, command=iperf_test,
                       hosts=hosts)
