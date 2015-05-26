Developing Plugins
------------------
Introduction
++++++++++++

The plugins in Calyptos are implemented with the `stevedore library <http://docs.openstack.org/developer/stevedore/>`_.
There are currently 2 different types of plugins:

* :ref:`Validators <validators>`
* :ref:`Debuggers <debuggers>`

We will go into more detail on each type of plugin below.

.. _validators:

Validators
++++++++++
Validator plugins are meant to ensure that the configuration file provided will produce a functional Eucalyptus cloud
when the deployer is run. The plugin has access to a RoleBuilder object which provides:

*  Access to the configuration yaml
*  Methods for relaying success and failure messages
*  A ``dict`` that groups each machine in the deployment by their role/component

This step does not block you from continuing to deploy, however it is intended to provide feedback
on configurations which we know will be suboptimal or simply non-functional.

The implemented plugins live in the ``eucadeploy/plugins/validator`` folder. Please add your validators there when
submitting a pull request.

Below is an example of a very simple validation plugin. In this example plugin we will merely be checking that we have
a CLC role defined and there is not more than 1 host in that group.

.. code-block:: python
   :linenos:

    from eucadeploy.plugins.validator.validatorplugin import ValidatorPlugin

    class CLCCheck(ValidatorPlugin):
        def validate(self):
            if 'clc' in self.role_builder.roles:
                self.success('Found at least 1 CLC')
                if len(self.role_builder.roles['clc']) == 1:
                    self.success('Found only 1 CLC')
                else:
                    self.failure('Found more than 1 CLC')
            else:
                self.failure('No CLCs found')

Lets break down this plugin and note the interesting/crucial bits:

* In lines 1 and 3, note that we must make our plugin inherit from the ``ValidatorPlugin`` base class
* In line 4, each validator plugin must override the ``validate`` method, this is what will be called by the CLI
* In line 5, we are grabbing the set of roles from the component_deployer, this is a dict of sets with each key being
  the name of the roles. Here we are simply checking that there exists a ``clc`` role
* In lines 6 and 8, we log and report the success of our validations
* In lines 10 and 12, we log and report the failure cases of our validations

In order to add our validator to the list of default plugins to run during the validation step we need to add it to the
entry points found in the ``setup.py`` file. Validators belong in the ``eucadeploy.validator`` array. If example plugin
was in the ``eucadeploy/plugins/validator/clccheck.py`` file we would add the following to the entrypoints:

.. code-block:: python

    'clccheck = eucadeploy.plugins.validator.clccheck:CLCCheck'

.. _debuggers:

Debuggers
+++++++++
Debuggers are used to introspect into a running system to:

* Retrieve relevant logs/info
* Check for resource contention (memory, disk, cpu)
* Ensure network connectivity is available between components

An example plugin for looking at the state of the node-controller service would look like this:

.. code-block:: python
   :linenos:

    from fabric.context_managers import hide
    import re
    from calyptos.plugins.debugger.debuggerplugin import DebuggerPlugin

    class DebugNodeControllerService(DebuggerPlugin):
        def debug(self):
            # Get the list of node controllers
            nodes = self.role_builder.roles['node-controller']
            # Collect service status using SSH to the hosts
            nc_service_state = self.run_command_on_hosts('service eucalyptus-nc status', hosts=nodes)
            # Iterate through the result from each node and flag it as a success or failure
            for node in nodes:
                if re.search('running', nc_service_state[node]):
                    self.success(node + ': NC service running')
                else:
                    self.failure(node + ': NC service not running')
            return self.passed, self.failed

