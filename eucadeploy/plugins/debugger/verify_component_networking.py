from fabric.context_managers import hide
import re
from eucadeploy.plugins.debugger.debuggerplugin import DebuggerPlugin

class VerifyComponentNetworking(DebuggerPlugin):
    def debug(self):
        all_hosts = self.component_deployer.all_hosts
        roles = self.component_deployer.get_roles()
        self.info('Verify recommended NIC configuration on all hosts')
        self._confirm_nics(all_hosts)
        #self.info('Verify multicast group communication between all'
        #          + ' Eucalyptus java components')
        #self._confirm_multicast(roles)

        return (self.passed, self.failed)

    def _confirm_nics(self, all_hosts):
        """
        """
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
     
                     
