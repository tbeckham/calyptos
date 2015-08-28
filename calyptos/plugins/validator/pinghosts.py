from calyptos.plugins.validator.validatorplugin import ValidatorPlugin
from fabric.colors import yellow
import threading
import subprocess



class PingHosts(ValidatorPlugin):
    hostlock = threading.Lock()

    def validate(self):
        results = {}
        threads = []

        def results_ping(host, count, hostlock):
            res = self.ping_ip(host, count=count)
            with hostlock:
                results[host] = res
        for host in self.component_deployer.all_hosts:
            t = threading.Thread(target=results_ping, args=(host, 3, self.hostlock))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        total_pings_failed = 0
        total_pings_passed = 0
        for host, result in results.iteritems():
            if result:
                self.success('Ping to ' + host)
                total_pings_passed += 1
            else:
                self.failure('Ping to ' + host)
                total_pings_failed += 1
        print yellow('--------------------------------------------------')
        print yellow('Total successful pings: ' + str(total_pings_passed))
        print yellow('Total failed pings: ' + str(total_pings_failed))
        print yellow('--------------------------------------------------')
        print ""

    def ping_ip(self, host, count=3):
        args = 'ping -W 3 -c {0} {1}'.format(count, host)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   bufsize=4096, shell=True)
        output, unused_err = process.communicate()
        retcode = process.poll()
        print output
        if retcode:
            return False
        return True
