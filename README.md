# Calyptos

This is a tool for managing your Eucalyptus deployments

# [Documentation](http://calyptos.readthedocs.org/en/latest/)

## Install

### On a CentOS 6 system:

    yum install -y python-devel gcc git python-setuptools
    git clone https://github.com/eucalyptus/calyptos
    cd calyptos
    python setup.py install
    
## Lifecycle Actions
The cloud lifecycle is broken down into many phases:

### Configure
The configuration is written in YAML. Examples can be found in the examples directory. For a full list of attributes that can be set look at the [Eucalyptus Cookbook attributes](https://github.com/eucalyptus/eucalyptus-cookbook/blob/testing/attributes/default.rb). Edit the etc/environment.yml file to match your deployment topology and configuration.

### Validate
In this stage we run validations against the configuration file to ensure that the deployment will succeed as we expect.

    calyptos validate -e <your-environment-file>

### Prepare
This step ensures that our dependencies are installed on all servers and that we can SSH to all of them. It is nice to know that we are on good footing before we get going with the deployment.

    calyptos prepare -p <root-ssh-password-for-deployment-systems>

### Bootstrap
This step deploys the CLC and initializes the database. Here we are getting a bit deeper and if complete, we can assume that we've are on good footing to continue deploying the rest of the cloud.

    calyptos bootstrap -p <root-ssh-password-for-deployment-systems>
  
### Provision
Provisions the rest of the system or update the configuration of an existing system. If you change anything in your environment.yml, you can use this to push that change out to your cloud.

    calyptos provision -p <root-ssh-password-for-deployment-systems>
    
### Debug
This step will grab all necessary information from a system in order to provide artifacts for use in debugging a problem.  In addition, this step will do the following:
* Confirm/install [sosreports](https://github.com/sosreport/sos) and [eucalyptus sosreports plugin](https://github.com/eucalyptus/eucalyptus-sosreport-plugins) on each node
* Run sosreports on each node
* Copy the sosreport back to the local client
```
    calyptos debug -p <root-ssh-password-for-deployment-systems>
```
    
