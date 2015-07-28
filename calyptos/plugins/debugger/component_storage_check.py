from __future__ import division
from fabric.context_managers import hide
import re
from calyptos.plugins.debugger.debuggerplugin import DebuggerPlugin

class CheckStorage(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        # Minimmum memory requirement for each cloud component in KB
        self.min_memory_req = 4000000
        # Minimmum disk space requirement for each cloud component in GB
        self.min_disk_req = 30
        self._verify_disk_storage(all_hosts)
        self._verify_memory_storage(all_hosts)

        return (self.passed, self.failed)

    def _verify_disk_storage(self, all_hosts):
        """
        Verifies minimum disk space requirement is met on each component.
        The Linux tool - df - is used for the validation.
        Disk minimum is defined in debuggerplugin.py
        
        :param all_hosts: a set of Eucalyptus cloud components
        """
        self.info('Minimum Disk Requirements Test on all hosts')
        df_output = 'df -h --sync /var/lib/eucalyptus -P -T --block-size G |' \
                    ' awk \'{print $3}\' | grep -v Size | grep -v blocks'
        with hide('everything'):
            disk_storage = self.run_command_on_hosts(df_output, all_hosts)
        
        for host in all_hosts:
            disk_size = int(disk_storage[host].strip('G'))
            if disk_size < self.min_disk_req:
                self.failure(host + ': ' + str(self.min_disk_req)
                             + ' gig minimum disk requirement'
                             + ' has not been met')
            else:
                self.success(host + ': ' + str(self.min_disk_req)
                             + ' gig minimum disk requirements met')

    def _verify_memory_storage(self, all_hosts):
        """
        Verifies mimimum memory requirement is met on each component.
        The Linux tool - free - is used for the validation.
        Memory minimum is defined in debuggerplugin.py

        :param all_hosts: a set of Eucalyptus cloud components
        """
        self.info('Minimum Memory Requirements Test on all hosts')
        mem_output = 'free | grep \'Mem:\' | awk \'{print $2}\''
        with hide('everything'):
            mem_storage = self.run_command_on_hosts(mem_output, all_hosts)

        for host in all_hosts:
            mem_size = int(mem_storage[host])
            min_memory = self.min_memory_req / 1000000
            if mem_size < self.min_memory_req:
                self.failure(host + ': ' + str(min_memory)
                             + ' gig minimum memory requirement'
                             + ' has not been met')
            else:
                self.success(host + ': ' + str(min_memory)
                            + ' gig minimum memory requirements met')
