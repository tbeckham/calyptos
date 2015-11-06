from calyptos.plugins.validator.validatorplugin import ValidatorPlugin


class VPC(ValidatorPlugin):

    def __init__(self, *args, **kwargs):
        super(VPC, self).__init__(*args, **kwargs)
        self.net_mode_path = ['default_attributes', 'eucalyptus', 'network', 'mode']
        self.mido_config_path = ['default_attributes', 'eucalyptus', 'network', 'config-json',
                                 'Mido']
        self.mido_gw_hostnames = []

    def _get_env_attr(self, path):
        context = self.environment
        for key in path:
            if isinstance(context, dict) and context.has_key(key):
                context = context.get(key)
            else:
                raise KeyError('Could not find config/env attribute:"{0}" in path:{1}'
                               .format(key, " -> ".join(path)))
        return context

    def validate(self):
        net_mode = self._get_env_attr(self.net_mode_path)
        if net_mode == 'VPCMIDO':
            # Make sure the mido config section is present
            self._get_env_attr(self.mido_config_path)
            # Parse out and validate the gateways
            self._check_mido_gateways()
            # Validate the mido host mapping section
            self._check_mido_host_mapping()

    def _check_mido_gateways(self):
        try:
            # Legacy schema
            mido_gw_hostnames = self._get_env_attr(self.mido_config_path + ['GatewayHost'])
        except KeyError as KE:
            gateways = []
            try:
                gateways = self._get_env_attr(self.mido_config_path + ['Gateways'])
            except KeyError as KE:
                self.failure(str(KE))
                return
            for gw in gateways:
                if not gw.get('GatewayHost', None):
                    self.failure('VPC - "GatewayHost" (hostname) for gateway missing or not '
                                 'defined')
                else:
                    self.success('VPC - "GatewayHost" defined: {0}'.format(gw.get('GatewayHost')))
                    self.mido_gw_hostnames.append(gw.get('GatewayHost'))
                if not gw.get('GatewayIP', None):
                    self.failure('VPC - "GatewayIP" (ip address) for gateway missing or not '
                                 'defined')
                else:
                    self.success('VPC - "GatewayIP" defined: {0}'.format(gw.get('GatewayIP')))
                if not gw.get('GatewayInterface', None):
                    self.failure('VPC - "GatewayInterface" (network interface) for gateway '
                                 'missing or not defined')
                else:
                    self.success('VPC - "GatewayInterface" defined: {0}'
                                 .format(gw.get('GatewayInterface')))

    def _check_mido_host_mapping(self):
        try:
            mapping = self._get_env_attr(['default_attributes', 'midokura',
                                          'midolman-host-mapping'])
            self.success('VPC - Midolman hostmapping exists')
        except KeyError as KE:
            self.failure(str(KE))
            return
        clc = self.component_deployer.roles['clc']
        nc = self.component_deployer.roles['node-controller']

        for hostname, ip in mapping.iteritems():
            if ip not in clc and ip not in nc and hostname not in self.mido_gw_hostnames:
                self.failure('VPC - The host {0}:{1} is in the Midolman host-mapping but is not '
                             'an NC, CLC, or Mido-GW'.format(hostname, ip))
            else:
                self.success('VPC - VPC midolman check: {0}:{1} is either an NCs, CLCs, '
                             'or MidoGateway'.format(hostname, ip))
        for ip in clc:
            if ip not in mapping.values():
                self.failure('VPC - Did not find clc ({0}) in Midolman host-mapping'.format(ip))
            else:
                self.success('VPC - CLC {0} is in the Midolman host-mapping'.format(ip))
        for ip in nc:
            if ip not in mapping.values():
                self.failure('VPC - Did not find NC ({0}) in Midolman host-mapping'.format(ip))
            else:
                self.success('VPC - NC {0} is in the midolman host-mapping'.format(ip))