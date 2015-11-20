from calyptos.plugins.validator.validatorplugin import ValidatorPlugin
import re

class VPC(ValidatorPlugin):

    def __init__(self, *args, **kwargs):
        super(VPC, self).__init__(*args, **kwargs)
        # Eucalyptus Network Config VPC Attribute Paths
        self.net_mode_path = ['default_attributes', 'eucalyptus', 'network', 'mode']
        self.mido_config_path = ['default_attributes', 'eucalyptus', 'network', 'config-json',
                                 'Mido']
        # Midokura Configuration Attribute Paths
        self.midokura_path = ['default_attributes', 'midokura']
        self.zookeepers_path = self.midokura_path + ['zookeepers']
        self.cassandras_path = self.midokura_path + ['cassandras']
        self.initial_tenant_path = self.midokura_path + ['initial-tenant']
        self.bgp_peers_path = self.midokura_path + ['bgp-peers']
        self.midonet_api_path = self.midokura_path + ['midonet-api-url']

        # Store Euca/Midonet Gateways Hostnames for verification purposes
        self.mido_gw_hostnames = []

    def validate(self):
        """
        Top level Validation Method
        """
        net_mode = self._get_env_attr(self.net_mode_path)
        if net_mode == 'VPCMIDO':
            # Make sure the mido config section is present
            self._get_env_attr(self.mido_config_path)
            # Parse out and validate the gateways
            self._check_mido_gateways()
            # Validate the mido host mapping section
            self._check_mido_host_mapping()
            # Validate zookeeper entry(s)
            self._check_zookeeper()
            # Validate Cassandra entry(s)
            self._check_cassandra()

    def _path_to_string(self, path):
        return "{0}".format(" -> ".join(path))

    def _get_env_attr(self, path):
        """
        Convenience method for inspecting the environment dict and providing debug/error
        info on missing attributes in the requested path.
        :raises :KeyError
        """
        context = self.environment
        for key in path:
            if isinstance(context, dict) and context.has_key(key):
                context = context.get(key)
            else:
                raise KeyError('Could not find config/env attribute:"{0}" in path:{1}'
                               .format(key, self._path_to_string(path)))
        return context


    def _check_mido_gateways(self):
        """
        Validate the Eucalyptus configuration for Mido Gateway(s). Validate the attribute
        presence, type(s), and format.
        """
        try:
            # Check for presence of the Legacy schema using the GatewayHost attribute...
            gateways_path = self.mido_config_path + ['GatewayHost']
            gateway_host = self._get_env_attr(gateways_path)
            if gateway_host:
                self.success('VPC - GatewayHost defined:{0}'.format(gateway_host))
                self.mido_gw_hostnames.append(gateway_host)
            else:
                self.failure('VPC - GatewayHost Attribute found empty at path:{0}'
                             .format(self._path_to_string(gateways_path)))
            try:
                # Check to make sure only one method of providing a gateway is present
                self.mido_config_path + ['Gateways']
                self.failure('Found both "Gateways" and the older "GatewayHost" config attributes '
                             'present in the Environment. Replace GatewayHost to use only the '
                             '"Gateways" list attribute instead')
            except KeyError:
                pass
        except KeyError as KE:
            # GatewayHost was not found so no check for the newer Gateways attribute...
            gateways = []
            try:
                gateways_path = self.mido_config_path + ['Gateways']
                gateways = self._get_env_attr(gateways_path)
                if not isinstance(gateways, list):
                    self.failure('Gateways:"{0}" not of type list at path:"{1}"'
                                 .format(gateways, self._path_to_string(gateways_path)))
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
        """
        Check that all hosts intended/expected to have Midolman running on them are present
        in the hostname to IP addr mapping attribute
        """
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

    def _check_cassandra(self):
        """
        Check that a Cassandra server(s) has been provided an the attribute is of 'list' type
        """
        try:
            cassandras = self._get_env_attr(self.cassandras_path)
        except KeyError as KE:
            self.failure(str(KE))
            return
        if not isinstance(cassandras, list):
            self.failure('VPC - Cassandras attribute not of type list at path:"{0}"'
                         .format(self._path_to_string(self.cassandras_path)))
            return
        self.success('VPC - Cassandra validation passed')

    def _check_zookeeper(self):
        """
        Check that the Zookeeper Server(s) have been provided.
        validate the list type, and validate the entry format
        """
        try:
            zookeepers = self._get_env_attr(self.zookeepers_path)
        except KeyError as KE:
            self.failure(str(KE))
            return
        if not isinstance(zookeepers, list):
            self.failure('VPC - Zookeepers attribute not of type list at path:"{0}"'
                         .format(self._path_to_string(self.zookeepers_path)))
            return
        entry_error = False
        for zk in zookeepers:
            ip_port = re.match('^\s*(\w.*):(\d+)\s*$', zk)
            if not ip_port or len(ip_port.groups()) != 2:
                self.failure('VPC - Zookeeper entry:"{0}" may not be of format:"IP:PORT"'
                             .format(zk))
                entry_error = True
        if not entry_error:
            self.success('VPC - Zookeeper validation passed')