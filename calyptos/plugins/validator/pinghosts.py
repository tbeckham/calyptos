from calyptos.plugins.validator.validatorplugin import ValidatorPlugin
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
        for host, result in results.iteritems():
            if result:
                self.success('Ping to ' + host)
            else:
                self.failure('Ping to ' + host)
                raise AssertionError('Unable to ping host: ' + host)

    def ping_ip(self, host, count=3):
        args = 'ping -W 3 -c {0} {1}'.format(count, host)
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   bufsize=4096, shell=True)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            print output
            return False
        return True
