import json
from fabric.operations import local
from fabric.colors import red, green
import yaml
from deployerplugin import DeployerPlugin
from fabric.context_managers import hide, warn_only, lcd
from fabric.tasks import execute
from calyptos.chefmanager import ChefManager
import os
from calyptos.rolebuilder import RoleBuilder


class Chef(DeployerPlugin):
    def __init__(self, password, environment_file='etc/environment.yml',
                 config_file='config.yml', debug=False, branch='euca-4.1',
                 cookbook_repo='https://github.com/eucalyptus/eucalyptus-cookbook', update_repo=True):
        self.chef_repo_dir = 'chef-repo'
        self.environment_file = environment_file
        if debug:
            self.hidden_outputs = []
        else:
            self.hidden_outputs = ['running', 'stdout', 'stderr']
        self.role_builder = RoleBuilder(environment_file)
        self.roles = self.role_builder.get_roles()
        self.all_hosts = self.roles['all']
        self._prepare_fs(cookbook_repo, branch, debug, update_repo)
        self.environment_name = self._write_json_environment()
        self.chef_manager = ChefManager(password, self.environment_name,
                                        self.roles['all'])
        self.config = self.get_chef_config(config_file)

    def _prepare_fs(self, cookbook_repo, branch, debug, update_repo):
        ChefManager.install_chef_dk()
        ChefManager.create_chef_repo()
        with hide(*self.hidden_outputs):
            local('if [ ! -d eucalyptus-cookbook ]; then '
                  'git clone '
                  '{0} eucalyptus-cookbook;'
                  'fi'.format(cookbook_repo))
            if update_repo:
                print green('updating eucalyptus-cookbook')
                local('cd eucalyptus-cookbook; git checkout {0};'.format(branch))
                local('cd eucalyptus-cookbook; git pull origin {0};'.format(branch))
        ChefManager.download_cookbooks('eucalyptus-cookbook/Berksfile',
                                       os.path.join(self.chef_repo_dir +
                                                    '/cookbooks'),
                                       debug=debug)

    @staticmethod
    def get_chef_config(config_file):
        full_config = yaml.load(open(config_file).read())
        if 'deployer' in full_config:
            if 'chef' in full_config['deployer']:
                return full_config['deployer']['chef']
            else:
                raise IndexError('Unable to find chef config in deployer section of config file')
        else:
            raise IndexError('Unable to find deployer section of config file')

    def _get_recipe_list(self, component):
        for recipe_dict in self.config['roles']:
            if component in recipe_dict:
                return recipe_dict[component]
        raise ValueError('No component found for: ' + component)

    def _write_json_environment(self):
        environment_dict = yaml.load(open(self.environment_file).read())
        current_environment = environment_dict['name']
        environment_dir = self.chef_repo_dir + '/environments/'
        filename = environment_dir + current_environment + '.json'
        with open(filename, 'w') as env_json:
            env_json.write(json.dumps(environment_dict, indent=4,
                                      sort_keys=True, separators=(',', ': ')))
        return current_environment

    def _get_environment(self):
        with open(self.chef_repo_dir + '/environments/' +
                  self.environment_name + '.json') as env_file:
            return json.loads(env_file.read())

    def _run_chef_on_hosts(self, hosts):
        with hide(*self.hidden_outputs):
            execute(self.chef_manager.push_deployment_data, hosts=hosts)
        with warn_only():
            results = execute(self.chef_manager.run_chef_client, hosts=hosts)
        failed = False
        for machine, result in results.iteritems():
            if result.succeeded:
                print green('Success on host: ' + machine)
            if result.failed:
                failed = True
                fail_log_name = 'calyptos-failure-' + machine + '.log'
                print red('Chef Client failed on ' + machine + ' log available at ' +  fail_log_name)
                with open(fail_log_name, 'w') as file:
                    file.write(result.stdout)
        if failed:
            exit(1)
        execute(self.chef_manager.pull_node_info, hosts=hosts)
        return results

    def prepare(self):
        self.chef_manager.sync_ssh_key(self.all_hosts)
        self.chef_manager.clear_run_list(self.all_hosts)
        order = [self.chef_manager.push_deployment_data,
                 self.chef_manager.bootstrap_chef,
                 self.chef_manager.run_chef_client,
                 self.chef_manager.pull_node_info]
        for method in order:
            with hide(*self.hidden_outputs):
                execute(method, hosts=self.all_hosts)
        print green('Prepare has completed successfully. Continue on to the bootstrap phase')

    def bootstrap(self):
        # Install CLC and Initialize DB
        if self.roles['mon-bootstrap']:
            mon_bootstrap = self.roles['mon-bootstrap']
            self.chef_manager.clear_run_list(self.all_hosts)
            self.chef_manager.add_to_run_list(mon_bootstrap, self._get_recipe_list('mon-bootstrap'))
            self._run_chef_on_hosts(mon_bootstrap)

        if self.roles['riak-head']:
            riak_head = self.roles['riak-head']
            self.chef_manager.clear_run_list(self.all_hosts)
            self.chef_manager.add_to_run_list(riak_head, self._get_recipe_list('riak-head'))
            self._run_chef_on_hosts(riak_head)

        if self.roles['midolman']:
            midolman_hosts = self.roles['midolman']
            self.chef_manager.add_to_run_list(midolman_hosts, ['midokura::midolman'])
            self._run_chef_on_hosts(midolman_hosts)

        if self.roles['clc']:
            self.chef_manager.clear_run_list(self.all_hosts)
            clc = self.roles['clc']
            self.chef_manager.add_to_run_list(clc, self._get_recipe_list('clc'))
            self._run_chef_on_hosts(clc)
        print green('Bootstrap has completed successfully. Continue on to the provision phase')

    def _pre_provision_check(self):
        if self.roles['clc']:
            clc_attributes = self.chef_manager.get_node_json(list(self.roles['clc'])[0])
            clc_euca_attributes = clc_attributes['normal']['eucalyptus']
            if 'cloud-keys' in clc_euca_attributes:
                keys = ['cloud-cert.pem', 'cloud-pk.pem', 'euca.p12']
                for key in keys:
                    if key not in clc_euca_attributes['cloud-keys']:
                        print red('Unable to find cloud keys {0} in CLC attributes'.format(clc_euca_attributes[key]))
                        print red('Re-run the bootstrap step and ensure that it is successful')
                        exit(1)
            else:
                print red('Unable to find cloud keys in CLC attributes')
                print red('Re-run the bootstrap step and ensure that it is successful')
                exit(1)

    def provision(self):
        self._pre_provision_check()
        # Install all other components and configure CLC
        self.chef_manager.clear_run_list(self.all_hosts)
        for role_dict in self.config['roles']:
            component_name = role_dict.keys().pop()
            self.chef_manager.add_to_run_list(self.roles[component_name],
                                              self._get_recipe_list(component_name))
        self._run_chef_on_hosts(self.all_hosts)

        if self.roles['riak-head']:
            riak_head = self.roles['riak-head']
            self.chef_manager.add_to_run_list(riak_head, ['riakcs-cluster::plancommit', 'riakcs-cluster::mergecreds'])
            self._run_chef_on_hosts(riak_head)

        if self.roles['clc']:
            clc = self.roles['clc']
            self.chef_manager.add_to_run_list(clc, ['eucalyptus::configure'])
            self._run_chef_on_hosts(clc)
            if self.role_builder.get_euca_attributes()['network']['mode'] == 'VPCMIDO':
                midonet_api = self.roles['midonet-api']
                create_resources = 'midokura::create-first-resources'
                self.chef_manager.add_to_run_list(midonet_api, [create_resources])
                self._run_chef_on_hosts(midonet_api)
        print green('Provision has completed successfully. Your cloud is now configured and ready to use.')

    def uninstall(self):
        self.chef_manager.clear_run_list(self.all_hosts)
        if self.roles['clc']:
            self.chef_manager.add_to_run_list(self.all_hosts, ['eucalyptus::nuke'])
        if self.roles['riak-head']:
            self.chef_manager.add_to_run_list(self.all_hosts, ['riakcs-cluster::nuke'])
        if self.roles['mon-bootstrap']:
            self.chef_manager.add_to_run_list(self.all_hosts, ['ceph-cluster::nuke'])
        if self.roles['haproxy']:
            self.chef_manager.add_to_run_list(self.all_hosts, ['haproxy::nuke'])
        self._run_chef_on_hosts(self.all_hosts)
        with lcd('chef-repo'):
            local('knife node bulk delete -z -E {0} -y ".*"'.format(self.environment_name))
        print green('Uninstall has completed successfully. Your cloud is now torn down.')
