import yaml


class RoleBuilder():

    # Global list of roles
    ROLE_LIST = ['clc',
                 'user-facing',
                 'console',
                 'walrus',
                 'cluster-controller',
                 'storage-controller',
                 'node-controller',
                 'midonet-api',
                 'midolman',
                 'mido-zookeeper',
                 'mido-cassandra',
                 'mon-bootstrap',
                 'ceph-mons',
                 'ceph-osds',
                 'riak-head',
                 'riak-node',
                 'haproxy',
                 'nginx',
                 'all']

    def __init__(self, environment_file='environment.yml'):
        self.environment_file = environment_file
        self.env_dict = self.get_all_attributes()
        self.roles = self.get_roles()
        self.all_hosts = self.roles['all']

    def read_environment(self):
        with open(self.environment_file) as env_file:
            return yaml.load(env_file.read())

    def get_all_attributes(self):
        env_dicts = self.read_environment()
        return env_dicts['default_attributes']

    def get_euca_attributes(self):
        try:
            return self.env_dict['eucalyptus']
        except:
            return None

    def get_riak_attributes(self):
        try:
            return self.env_dict['riakcs_cluster']
        except:
            return None

    def get_ceph_attributes(self):
        try:
            return self.env_dict['ceph']
        except:
            return None

    def _initialize_roles(self):
        roles = {}
        for role in self.ROLE_LIST:
            roles[role] = set()
        return roles

    def get_euca_hosts(self):
        roles = self.get_roles()

        # Create set of Eucalytpus only componnents
        euca_components = ['user-facing', 'cluster-controller',
                           'storage-controller', 'node-controller']
        if roles['walrus']:
            euca_components.append('walrus')

        all_hosts = roles['clc']
        for component in euca_components:
            all_hosts.update(roles[component])
        return all_hosts

    def get_roles(self):
        roles = self._initialize_roles()
        euca_attributes = self.get_euca_attributes()
        ceph_attributes = self.get_ceph_attributes()
        riak_attributes = self.get_riak_attributes()

        roles['all'] = set([])

        if riak_attributes:
            riak_topology = riak_attributes['topology']
            if riak_topology['head']:
                roles['riak-head'] = set([riak_topology['head']['ipaddr']])
                roles['all'].add(riak_topology['head']['ipaddr'])
            else:
                raise Exception("No head node found for RiakCS cluster!")

            if riak_topology.get('nodes'):
                for n in riak_topology['nodes']:
                    roles['riak-node'].add(n)
                    roles['all'].add(n)
            if riak_topology.get('load_balancer'):
                riak_lb = None
                if self.env_dict.get('nginx'):
                    riak_lb = 'nginx'
                    raise Exception("Nginx: Not implemented yet.")
                elif self.env_dict.get('haproxy'):
                    riak_lb = 'haproxy'
                else:
                    raise Exception("No Load-Balancer found for RiakCS cluster.")
                roles[riak_lb] = set([riak_topology['load_balancer']])
                roles['all'].add(riak_topology['load_balancer'])

        if ceph_attributes:
            ceph_topology = ceph_attributes['topology']
            if ceph_topology.get('mons'):
                mon_bootstrap = set()
                monset = set()
                for mon in ceph_topology['mons']:
                    if mon.get('init') and not mon_bootstrap:
                        mon_bootstrap.add(mon['ipaddr'])
                    monset.add(mon['ipaddr'])
                    roles['all'].add(mon['ipaddr'])
                if not mon_bootstrap:
                    raise Exception("No Initial Ceph Monitor found! Please mention at least one initial monitor.\n"
                                    "e.g\n"
                                    "mons:\n"
                                    "  - ipaddr: '10.10.1.5'\n"
                                    "    hostname: 'node1'\n"
                                    "    init: true")
                roles['ceph-mons'] = monset
                roles['mon-bootstrap'] = mon_bootstrap

            if ceph_topology['osds']:
                osdset = set()
                for osd in ceph_topology['osds']:
                    osdset.add(osd['ipaddr'])
                    roles['all'].add(osd['ipaddr'])
                roles['ceph-osds'] = osdset
            else:
                raise Exception("No OSD Found!")

        if euca_attributes:
            topology = euca_attributes['topology']

            # Add CLC
            roles['clc'] = set([topology['clc-1']])
            roles['all'].add(topology['clc-1'])

            # Add UFS
            roles['user-facing'] = set(topology['user-facing'])
            for ufs in topology['user-facing']:
                roles['all'].add(ufs)

            # add console
            if 'console' in topology:
                roles['console'] = set(topology['console'])
                for console in topology['console']:
                    roles['all'].add(console)

            # Add Walrus
            if 'walrus' in topology:
                roles['walrus'] = set([topology['walrus']])
                roles['all'].add(topology['walrus'])
            else:
                # No walrus defined assuming RiakCS
                roles['walrus'] = set()

            # Add cluster level components
            for name in topology['clusters']:
                roles['cluster'] = {}
                if 'cc-1' in topology['clusters'][name]:
                    cc = topology['clusters'][name]['cc-1']
                    roles['cluster-controller'].add(cc)
                else:
                    raise IndexError("Unable to find CC in topology for cluster " + name)

                if 'sc-1' in topology['clusters'][name]:
                    sc = topology['clusters'][name]['sc-1']
                    roles['storage-controller'].add(sc)
                else:
                    raise IndexError("Unable to find SC in topology for cluster " + name)

                roles['cluster'][name] = set([cc, sc])
                if 'nodes' in topology['clusters'][name]:
                    nodes = topology['clusters'][name]['nodes'].split()
                else:
                    raise IndexError("Unable to find nodes in topology for cluster " + name)
                for node in nodes:
                    roles['node-controller'].add(node)
                    roles['cluster'][name].add(node)
                roles['all'].update(roles['cluster'][name])

            # Add Midokura roles
            midokura_attributes = self.env_dict.get('midokura', None)
            if midokura_attributes and euca_attributes['network']['mode'] == 'VPCMIDO':
                mido = euca_attributes['network']['config-json']['Mido']
                mido_gw_hostname = mido.get('EucanetdHost', None)
                midolman_host_mapping = midokura_attributes.get('midolman-host-mapping', None)
                if midolman_host_mapping:
                    mido_api_ip = midolman_host_mapping.get(mido_gw_hostname, None)
                    if not mido_api_ip:
                        raise Exception('Unable to find midonet-api ({0}) host '
                                        'in midolman-host-mapping'.format(mido_gw_hostname))
                    # Add the host IP for the midonet gw
                    roles['midonet-api'].add(mido_api_ip)
                    # Add hosts from the midonet host mapping, and all nodes
                    for hostname, host_ip in midolman_host_mapping.iteritems():
                        roles['midolman'].add(host_ip)
                    for node in roles['node-controller']:
                        roles['midolman'].add(node)
                for host in self.env_dict.get('midokura', {}).get('zookeepers', []):
                    roles['mido-zookeeper'].add(str(host).split(':')[0])
                    roles['all'].add(str(host).split(':')[0])
                for host in self.env_dict.get('midokura', {}).get('cassandras', []):
                    roles['mido-cassandra'].add(host)
                    roles['all'].add(host)
        return roles
