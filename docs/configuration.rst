Calyptos Configuration File
***************************

.. contents:: :local:

Calyptos configuration files are written in `YAML syntax <http://en.wikipedia.org/wiki/YAML/>`_.
Below is a guide on what can be provided and how to structure your configuration files.

The a typical config file has the following structure::

    name: HadEupa
    description: This Euca install will run our Hadoop workloads!
    default_attributes:
      eucalyptus:
        topology:
          clc-1: 10.111.5.138
          user-facing:
          - 10.111.5.138
          walrus: 10.111.5.138
          clusters:
            hadoop-a:
              cc-1: 10.111.5.138
              nodes: 10.111.5.102
              sc-1: 10.111.5.138
        network:
          mode: EDGE
          private-interface: br0
          public-interface: br0
          bridge-interface: br0
          bridged-nic: em1
          config-json:
            Clusters:
            - Name: hadoop-a
              PrivateIps:
              - 10.111.31.43-10.111.31.50
              Subnet:
                Gateway: 10.111.0.1
                Name: 10.111.0.0
                Netmask: 255.255.0.0
                Subnet: 10.111.0.0
            InstanceDnsServers:
            - 10.111.5.138
            PublicIps:
            - 10.111.31.35-10.111.31.42
        system-properties:
          cloudformation.url_domain_whitelist: '*s3.amazonaws.com,*qa1.eucalyptus-systems.com'

Lets take a look at each section and figure out what each does.

Name
----
This is a short name used to refer to your cloud. It must not contain any spaces or underscores.

Description
-----------
This can be a sentence that further identifies your cloud and its purpose moving forward.

Default Attributes
------------------
Default attributes are applied to all machines in your deployment. These can be seen as "global" configuration values.
This section is broken down by subsystem. For example, there are sections for:
* eucalyptus
* midokura
* riakcs
In each of these sections we can configure and tune each set of components that make up our cloud infrastructure. Lets
take a look at each section more in depth.

eucalyptus
^^^^^^^^^^
The eucalyptus section is likely to be the one most heavily interacted with. This section helps to define the Eucalyptus
specific configuration of your deployment. This includes but isn't limited to:
* Component topology
* Networking configuration
* System properties

topology
""""""""
Example::

    topology:
      clc-1: 10.111.5.138
      user-facing:
      - 10.111.5.138
      walrus: 10.111.5.138
      clusters:
        hadoop-a:
          cc-1: 10.111.5.138
          nodes: 10.111.5.102
          sc-1: 10.111.5.138

This section describes not only where to connect to your hosts but also which components should be installed on each.
The cloud global components are defined by the following keys in the topology section:
* ``clc-1``: The primary cloud controller host
* ``user-facing``: A list of user-facing service hosts
* ``walrus``: The host to install the walrus on
The cluster level components are defined in a dictionary where the key is the intended name of the cluster. In our example
above the cluster name is ``hadoop-a``. Inside each of the specific cluster sections the following hosts must be defined:
* ``cc-1``: The primary cluster controller
* ``sc-1``: The primary storage controller
* ``nodes``: This is a space separated string of the node controllers in this cluster

network
"""""""
Example::

    network:
      mode: EDGE
      private-interface: br0
      public-interface: br0
      bridge-interface: br0
      bridged-nic: em1
      config-json:
        Clusters:
        - Name: hadoop-a
          PrivateIps:
          - 10.111.31.43-10.111.31.50
          Subnet:
            Gateway: 10.111.0.1
            Name: 10.111.0.0
            Netmask: 255.255.0.0
            Subnet: 10.111.0.0
        InstanceDnsServers:
        - 10.111.5.138
        PublicIps:
        - 10.111.31.35-10.111.31.42

The network section defines global attributes for cloud level networking as well as the networking parameters that are
used on the node controllers.

The mode is a string that can be one of the following:
    * EDGE
    * VPCMIDO
    * MANAGED
    * MANAGED-NOVLAN

The following params are available at the global level:
    * ``private-interface`` and ``public-interface keys`` - map to the ``VNET_PRIVINTERFACE`` and ``VNET_PUBINTERFACE``
      respectively for the eucalyptus.conf on both cluster and node controllers
    * ``bridge-interface`` - maps to the ``VNET_BRIDGE`` parameter in eucalyptus.conf for node controllers

The ``config-json`` section has the same structure `as defined in the Eucalyptus documentation <https://www.eucalyptus.com/docs/eucalyptus/4.1.1/index.html#install-guide/nw_edge_ha.html>`_.

system-properties
"""""""""""""""""
Example::

    system-properties:
      cloudformation.url_domain_whitelist: '*s3.amazonaws.com,*qa1.eucalyptus-systems.com'

This section allows the overriding of Eucalyptus system properties that would usually be set using ``euca-modify-property``.
Each key in this section is the name of a property, its corresponding value is what we will set that property to during
deployment. In the case of the example above we will run the following after the cloud has been fully deployed::

    euca-modify-property -p cloudformation.url_domain_whitelist='*s3.amazonaws.com,*qa1.eucalyptus-systems.com'

midokura
^^^^^^^^
Example::

  midokura:
    bgp-peers:
    - local-as: 65949
      peer-address: 10.116.133.173
      port-ip: 10.116.133.162
      remote-as: 65000
      route: 10.116.151.0/24
      router-name: eucart
    cassandras:
    - 10.111.5.162
    initial-tenant: euca_tenant_1
    midolman-host-mapping:
      b-19.qa1.eucalyptus-systems.com: 10.111.1.19
      g-15-01.qa1.eucalyptus-systems.com: 10.111.5.162
    midonet-api-url: http://10.111.5.162:8080/midonet-api
    repo-password: 8yU8Pj6h
    repo-url: http://eucalyptus:8yU8Pj6h@yum.midokura.com/repo/v1.8/stable/RHEL/6/
    repo-username: eucalyptus
    yum-options: --nogpg
    zookeepers:
    - 10.111.5.162:2181

RiakCS
^^^^^^
To deploy and use a RiakCS cluster, the configuration files need to have few sections e.g riak, riak_cs, sysctl, haproxy, riakcs_cluster.

riak_cs
"""""""
Example::

  riak_cs: (Config for RiakCS)
    config:
      riak_cs:
        anonymous_user_creation: true (boolean; default: true; required)
        fold_objects_for_list_keys: true (boolean; default: true; required)
        admin_key": "admin-key" (string; default: "admin-key"; required)
        admin_secret": "admin-secret" (string; default: "admin-secret"; required)
        cs_port: 8080 (int; default: 8080; required; can be any usable port)

riak
""""
Example::

  riak:
    config:
      riak_kv:
        storage_backend: "riak_cs_kv_multi_backend" (string; default: "riak_cs_kv_multi_backend"; required; default value is required for RiakCS deployment)

sysctl
""""""
Example::

  sysctl:
    params: (following params are required to avoid riak-diag warnings)
      net.core.wmem_default: "8388608"
      net.core.rmem_default: "8388608"
      net.core.wmem_max: "8388608"
      net.core.rmem_max: "8388608"
      net.core.netdev_max_backlog: "10000"

haproxy
"""""""
Example::

  haproxy: (required if riak_cs cluster is being placed behind load-balancer)
    incoming_port: 80 (int; default: 80; required; can be any usable port)
    members:
      - "server <host-01> <ip_address_of_riakcs_host-01>:<cs_port value from riak_cs config> weight 1 maxconn 256000 check"
      - "server <host-02> <ip_address_of_riakcs_host-02>:<cs_port value from riak_cs config> weight 1 maxconn 256000 check"
      - "server <host-03> <ip_address_of_riakcs_host-03>:<cs_port value from riak_cs config> weight 1 maxconn 256000 check"

riakcs_cluster
""""""""""""""
Example::

  riakcs_cluster: (Config for RiakCS Cluster)
    topology:
      head: (A host where calyptos bootstraps and creates necessary artifacts for the entire cluster)
        ipaddr: "ip_address of the head node" (string; required)
        fqdn: "host_name of the head node" (string; required)
      stanchion_ip: "ip_address for the stanchion host" (string; required)
      stanchion_port: 8085 (int; default: 8085; required; port for the stanchion host")
      load_balancer: "ip_address" (string; required; where load balancer should be installed for riak_cs cluster)
      nodes:
      - "ip_address" (string; required; ip_address for riakcs nodes)
      - "ip_address" (string; required; ip_address for riakcs nodes)

Ceph
^^^^
To deploy and use a RiakCS cluster, the configuration files need to have few sections e.g riak, riak_cs, sysctl, haproxy, riakcs_cluster.

ceph
""""
Example::

  ceph: (Config for Ceph Cluster)
    config:
      fsid: "unique id, e.g uuid" (string; required)
    topology:
      mon_bootstrap:
        ipaddr: "ip address of a mon host where calyptos bootstraps"
        hostname: "hostname of bootstrap mon host"
      osds:
        - ipaddr: "ip address of an osd host"
          hostname: "hostname of an osd host"
        - ipaddr: "ip address of an osd host"
          hostname: "hostname of an osd host"
          drive: (if using drives for OSDs, if not present, filesystem will be used for single OSD)
            - "drive name if not using OS drive e.g /dev/osd1 [optional]"
            - "drive name if not using OS drive e.g /dev/osd2 [optional]"
