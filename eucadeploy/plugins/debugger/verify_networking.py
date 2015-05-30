import fabric
from fabric.colors import white
from fabric.decorators import task
from fabric.operations import run, settings, local
from fabric.state import env
from fabric.tasks import execute
from fabric.context_managers import hide
import re
from eucadeploy.plugins.debugger.debuggerplugin import DebuggerPlugin

class VerifyConnectivity(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        self.info('Confirm iperf has been installed on'
                  + ' all components')
        self._install_conn_tool(all_hosts)
        self.info('Verify End-User Connectivity to User Facing'
                  + ' Services and Cloud Controller')
        end_user_services = roles['clc']
        end_user_services.update(roles['user-facing'])
        self._verify_enduser_access(end_user_services)
        self.info('Verify Eucalyptus Component communication'
                  + ' to the Storage Controller')
        self._verify_storage_controller_comms(roles)
        self.info('Verify Eucalyptus Component communication'
                  + ' to the Object Storage Gateway')
        #self._verify_osg_communication(roles)
        self.info('Confirm Eucalyptus Java components'
                  + ' can communicate with database on'
                  + ' Cloud Controller component')
        java_components = roles['clc']

        euca_java_roles = ['user-facing', 'storage-controller']
        if roles['walrus']:
            euca_java_roles.append('walrus')

        for component in euca_java_roles:
            java_components.update(roles[component])
        #self._verify_java_db_comms(roles['clc'],
        #                           java_components)
        
        self.info('Verify proper connectivity between'
                  + ' Cloud Controller and Cluster'
                  + ' Controller(s)')
        #self._verify_clc_cc_comms(roles['clc'],
        #                          roles['cluster-controller'])
  
        self.info('Verify proper connectivity between'
                  + ' Node Controllers and User'
                  + ' Facing Service(s)')
        #self._verify_ufs_nc_comms(roles['user-facing'],
        #                          roles['node-controller'])



        return (self.passed, self.failed)

    def _install_conn_tool(self, all_hosts):
        """
        Install iperf on all components in order to
        perform network connectivity tests.

        :param all_hosts: set of all Eucalyptus components
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
        Verify User Facing Service(s) and Node Controller
        can communicate to the Storage Controller on TCP port 8773.

        :param roles: set of roles (cloud components) for a given 
                      Eucalyptus cloud
        """
        for sc in roles['storage-controller']:
            iperf_cmd = 'iperf -c ' + sc + ' -T 32 -t 3 -i 1 -p 8773'
            with hide('everything'):
                iperf_result = self.execute_iperf_on_hosts(iperf_cmd,
                                                           roles['user-facing'])    
            for ufs in roles['user-facing']:
                flag = False
                for output in iperf_result[ufs].strip().split('\n'):
                    if re.search('Connection refused', output):
                        flag = True

                if flag:
                    self.failure(ufs + ':User Facing Service was not able'
                                 + ' to connect to Storage Controller '
                                 + sc + ' on TCP port 8773')
                else:
                    self.success(ufs + ':User Facing Service successfully'
                                 + ' connected to Storage Controller '
                                 + sc + ' on TCP port 8773')
            


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
