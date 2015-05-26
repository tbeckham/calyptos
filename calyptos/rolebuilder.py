import yaml


class RoleBuilder():

    # Global list of roles
    ROLE_LIST = ['clc', 'user-facing', 'midonet-gw',
                 'cluster-controller', 'storage-controller',
                 'node-controller', 'midolman', 'all']

    def __init__(self, environment_file='environment.yml'):
        self.environment_file = environment_file
        self.roles = self.get_roles()
        self.all_hosts = self.roles['all']

    def read_environment(self):
        return yaml.load(open(self.environment_file).read())

    def get_euca_attributes(self):
        env_dict = self.read_environment()
        return env_dict['default_attributes']['eucalyptus']

    def _initialize_roles(self):
        roles = {}
        for role in self.ROLE_LIST:
            roles[role] = set()
        return roles

    def get_roles(self):
        roles = self._initialize_roles()
        euca_attributes = self.get_euca_attributes()
        topology = euca_attributes['topology']

        # Add CLC
        roles['clc'] = set([topology['clc-1']])
        roles['all'] = set([topology['clc-1']])

        # Add UFS
        roles['user-facing'] = set(topology['user-facing'])
        for ufs in topology['user-facing']:
            roles['all'].add(ufs)

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
        if euca_attributes['network']['mode'] == 'VPCMIDO':
            roles['midolman'] = roles['node-controller']
            roles['midonet-gw'] = roles['clc']
        return roles
