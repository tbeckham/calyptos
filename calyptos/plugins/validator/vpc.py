from calyptos.plugins.validator.validatorplugin import ValidatorPlugin


class VPC(ValidatorPlugin):

    def validate(self):
        try:
            net_mode = self.environment['default_attributes']['eucalyptus']['network']['mode']
        except KeyError:
            raise KeyError('Unable to find network mode in environment.')
        if net_mode == 'VPCMIDO':
            self._check_mido_host_mapping()

    def _check_mido_host_mapping(self):
        try:
            mapping = self.environment['default_attributes']['midokura']['midolman-host-mapping']
            self.success('Midolman hostmapping exists')
        except KeyError:
            self.failure('Unable to find midonet host mapping at default_attributes->midokura->midolman-host-mapping')
            return
        clc = self.component_deployer.roles['clc']
        nc = self.component_deployer.roles['node-controller']
        midogw = self.environment['default_attributes']['eucalyptus']['network']['config-json']['Mido']['GatewayHost']
        for hostname, ip in mapping.iteritems():
            if ip not in clc and ip not in nc and hostname != midogw:
                self.failure('The host {0} is in the Midolman host-mapping but is not an NC or CLC'.format(ip))
            else:
                self.success('VPC midolman check: {0} is either an NCs, CLCs, or MidoGateway'.format(ip))
        for ip in clc:
            if ip not in mapping.values():
                self.failure('Did not find clc ({0}) in Midolman host-mapping'.format(ip))
            else:
                self.success('CLC {0} is in the midolman host-mapping'.format(ip))
        for ip in nc:
            if ip not in mapping.values():
                self.failure('Did not find NC ({0}) in Midolman host-mapping'.format(ip))
            else:
                self.success('NC {0} is in the midolman host-mapping'.format(ip))