from fabric.context_managers import hide
import re
from eucadeploy.plugins.debugger.debuggerplugin import DebuggerPlugin

class CheckStorage(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()

        self.info('Minimum Disk Requirements Test on all hosts')
        self._verify_disk_storage(all_hosts)
        self.info('Minimum Memory Requirements Test on all hosts')
        self._verify_memory_storage(all_hosts)

        return (self.passed, self.failed)

    def _verify_disk_storage(self, all_hosts):
        df_output = 'df -h --sync /var/lib/eucalyptus -P -T --block-size G |' \
                    ' awk \'{print $3}\' | grep -v Size | grep -v blocks'
        with hide('everything'):
            disk_storage = self.run_command_on_hosts(df_output, all_hosts)
        
        for host in all_hosts:
            disk_size = int(disk_storage[host].strip('G'))
            if disk_size < 30:
                self.failure(host + ': 30 gig minimum disk requirement'
                             + ' has not been met')
            else:
                self.success(host + ': 30 gig minimum disk requirements met')

    def _verify_memory_storage(self, all_hosts):
        mem_output = 'free | grep \'Mem:\' | awk \'{print $2}\''
        with hide('everything'):
            mem_storage = self.run_command_on_hosts(mem_output, all_hosts)

        for host in all_hosts:
            mem_size = int(mem_storage[host])
            if mem_size < 4000000:
                self.failure(host + ': 4 gig minimum memory requirement'
                             + ' has not been met')
            else:
                self.success(host + ': 4 gig minimum memory requirements met')
