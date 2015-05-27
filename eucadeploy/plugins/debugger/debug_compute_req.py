from fabric.context_managers import hide
import re
from eucadeploy.plugins.debugger.debuggerplugin import DebuggerPlugin

class CheckComputeRequirements(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        self.info('Operation System and Processor verification on all hosts')
        self._verify_os_proc(all_hosts)
        self.info('NTP/NTPD Test on all hosts')
        self._verify_clocks(all_hosts)
        self.info('Confirm virtualization is enabled on Node Controllers')
        self._check_virtualization(roles['node-controller'])

        return (self.passed, self.failed)

    def _verify_os_proc(self, all_hosts):
        """
        Verifies supported OS, correct chip architecture and 
        recommended minimum number of processors on all cloud components.  
        """
        os_output = 'cat /etc/system-release' 
        with hide('everything'):
            os_version = self.run_command_on_hosts(os_output, all_hosts)
       
        os_search_string = '(CentOS|Red).*(' + str(self.os_version) + '.\w+)' 
        for host in all_hosts:
            if re.search(os_search_string, os_version[host]):
                self.success(host + ': Correct OS Version')
            else:
                self.failure(host + ': Incorrect OS Version')
        
        arch_output = 'uname -m'
        with hide('everything'):
            arch_version = self.run_command_on_hosts(arch_output, all_hosts)

        for host in all_hosts:
            if re.search('x86_64', arch_version[host]):
                self.success(host + ': Correct chip architecture')
            else:
                self.failure(host + ': Incorrect chip architecture')

        cpu_output = 'cat /proc/cpuinfo | grep processor'        
        cputype_output = 'cat /proc/cpuinfo | grep \"model name\"'
        with hide('everything'):
            cpu_count = self.run_command_on_hosts(cpu_output, all_hosts)
            cpu_type = self.run_command_on_hosts(cputype_output, all_hosts)

        for host in all_hosts:
            cpus = re.findall('processor', cpu_count[host])
            if len(cpus) >= 2:
                self.success(host + ': Passed minimum number of'
                            + ' processors requirement')
            else:
                self.failure(host + ': Failed minimum number of'
                            + ' processors requirement')

            proc_type = re.findall('(model).*([Intel|AMD].*)\w+',
                                   cpu_type[host])
          
            if len(cpus) == len(proc_type):
                self.success(host + ': Passed requirement of '
                             + 'Intel/AMD processor support')
            else:
                self.failure(host + ': Failed requirement of '
                             + 'Intel/AMD processor support')


    def _verify_clocks(self, all_hosts):
        """
        Verifies that ntp, and ntpdate are installed on each 
        cloud component.  In addition, confirms components clock 
        skew isn't greater than the default maximum clock skew allowed for
        the cloud 
        """
        packages = ['ntp', 'ntpdate']
        for package in packages:
            with hide('everything'):
                # Use rpm --query --all to confirm packages exist
                rpm_output = self.run_command_on_hosts('rpm '
                             + '--query --all ' + package,
                             all_hosts)
            for host in all_hosts:
                if re.search(package, rpm_output[host]):
                    self.success(host + ':Package found - ' + package)
                else:
                    self.failure(host + ':Package not found - ' + package)

        service_output = 'service ntpd status'
        with hide('everything'):
            ntpd_output = self.run_command_on_hosts(service_output, all_hosts)

        for host in all_hosts:
            if re.search('running', ntpd_output[host]):
                self.success(host + ':ntpd running')
            else:
                self.failure(host + ':ntpd not running')

        # Check to see if ntpd is set to default-start runlevel 
        chkconfig_output = 'chkconfig --list ntpd | awk \'{print $4,$5,$6,$7}\''
        with hide('everything'):
            runlevel_output = self.run_command_on_hosts(chkconfig_output,
                                                        all_hosts)

        for host in all_hosts:
            if re.search('off', runlevel_output[host]):
                self.failure(host + ':runlevel for ntpd'
                             + ' has not been set to default-start')
            else:
                self.success(host + ':runlevel for ntpd'
                             + ' has been set to default-start')

        """
        Compare date across all cloud components. Date is compared in UTC
        format.  In addition, compare time on each cloud component, and 
        confirm there isn't more than the clock skew (in seconds) between
        all components.
        """
        date_output = 'date --utc +%m%d%y'
        time_output = 'date --utc +%H%M%S'    
        with hide('everything'):
            date_stamp = self.run_command_on_hosts(date_output, all_hosts)
            time_stamp = self.run_command_on_hosts(time_output, all_hosts)
       
        host_dates = []
        host_times = []
        for host in all_hosts:
            if not date_stamp[host] or not time_stamp[host]:
                self.failure(host + ': No date returned. Make sure machine clock'
                             + ' is set and synced across all nodes')
                return
            else:
                host_dates.append(date_stamp[host])
                host_times.append(time_stamp[host])
        
        if all(date == host_dates[0] for date in host_dates):
            self.success('All cloud components are using the same date')
        else:
            self.failure('Date is not consistent across cloud components')
 
        max_time = max(host_times) 
        for time in host_times:
            if abs(int(max_time) - int(time)) > int(self.clock_skew_sec):
                self.failure('Clock skew is greater than 1 minute across hosts.'
                             + ' Please confirm clocks are synced across all hosts.')
                return
        self.success('Clocks are synced within allowed threshold')   

    def _check_virtualization(self, nodes):
        """
        Confirm that node controller(s) have hardware virtualization
        enabled on either Intel or AMD chips.
        """
        virt_output = 'egrep -m1 -w \'^flags[[:blank:]]*:\' /proc/cpuinfo |' \
                      ' egrep -wo \'(vmx|svm)\''
        with hide('everything'):
            virt_test = self.run_command_on_hosts(virt_output, nodes)

        for host in nodes:
            if re.match('(vmx|svm)', virt_test[host]):
                self.success(host + ': Passed requirement of '
                            + 'Intel/AMD hardware virtualization support')
            else:
                self.failure(host + ': Failed requirement of '
                            + 'Intel/AMD hardware virtualization support')
