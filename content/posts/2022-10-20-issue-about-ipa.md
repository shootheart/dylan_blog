---

title: "关于Ironic Python Agent(IPA)v1.2.3适配CentOS9的问题"
date: 2022-10-20T00:00:00+08:00
toc: true
tags: ["OpenStack", "Python"]
categories: ["饭碗"]

---

### 报错：Temporary failure in name resolution

-  小镜象可以在裸机上正常启动，但是立即被ironic-conductor执行了关机操作 
-  观察ironic-conductor的debug日志，发现是无法与裸机建立连接，连接信息显示无法解析主机名 
```bash
2022-10-13 22:57:56.988 35448 ERROR ironic.drivers.modules.agent_client [req-75897e59-640c-4ce6-8fa3-d759f568c42a - - - - -] Error invoking agent command iscsi.start_iscsi_target for node f80db967-a8d4-4a05-9443-41b0855f1ec3
. Error: HTTPConnectionPool(host='172.25.134.128%20uid%200', port=9999): Max retries exceeded with url: /v1/commands?wait=true (Caused by NewConnectionError('<requests.packages.urllib3.connection.HTTPConnection object at 0x4
4e2310>: Failed to establish a new connection: [Errno -3] Temporary failure in name resolution',))
```
 

-  这里显示要连接的主机名非常奇怪，包含有某些转义的字符，查找发现`%20`代表的是空格，也就是这个主机名是`172.25.134.128 uid 0`，这当然无法解析。 
-  这个报错出自`ironic.drivers.modules.agent_client`中的`iscsi.start_iscsi_target`，`iscsi.start_iscsi_target`调用`iscsi._command`来发送请求 
```python
def _command(self, node, method, params, wait=False):
    ...
    try:
            response = self.session.post(url, params=request_params, data=body)
    except requests.RequestException as e:
            msg = (_('Error invoking agent command %(method)s for node '
                     '%(node)s. Error: %(error)s') %
                   {'method': method, 'node': node.uuid, 'error': e})
            LOG.error(msg)
            raise exception.IronicException(msg)
 	...
```
 

-  post请求中的`url`，是取自ironic node的`driver_internal_info/agent_url`，所以错误源自这个数据。 
-  如果仅仅是这个错误，可以先在ironic节点上配置这个主机名的映射，看跳过这个错误后是否还有其它问题。 

### 报错：iSCSI connection not seen by file system

-  手动跳过host解析的问题后，重新部署发现，ironic无法找到iscsi连接 
-  裸机的系统盘，是通过iscsi连接到ironic节点上进行镜像拷贝的，在ironic节点上，可以通过`iscsiadm -m node -S`来查看已连接的target，而ironic-conductor也调用了这个命令 
-  我们手动执行这个命令，发现已经有连接信息了，并且在`/dev/disk/by-path/`下也可以看到连接的iscsi设备，这说明ironic-conductor是没有找到设备 
-  日志中体现这个报错是在`ironic/drivers/modules/deploy_utils.py`中的`check_file_system_for_iscsi_device`方法报出的，这个方法定义如下： 
```python
def check_file_system_for_iscsi_device(portal_address,
                                       portal_port,
                                       target_iqn):
    """Ensure the file system sees the iSCSI block device."""
    check_dir = "/dev/disk/by-path/ip-%s:%s-iscsi-%s-lun-1" % (portal_address,
                                                               portal_port,
                                                               target_iqn)
    total_checks = CONF.disk_utils.iscsi_verify_attempts
    for attempt in range(total_checks):
        if os.path.exists(check_dir):
            break
        time.sleep(1)
        LOG.debug("iSCSI connection not seen by file system. Rechecking. "
                  "Attempt %(attempt)d out of %(total)d",
                  {"attempt": attempt + 1,
                   "total": total_checks})
    else:
        msg = _("iSCSI connection was not seen by the file system after "
                "attempting to verify %d times.") % total_checks
        LOG.error(msg)
        raise exception.InstanceDeployFailure(msg)
```
 

-  它会检查`/dev/disk/by-path`下是否存在iscsi设备，文件名根据传入的三个参数组合。 
-  我们在这里可以添加一个debug日志，把实际的`check_dir`打出，看是哪一个参数导致的错误。 
-  再次重新部署，我们发现了这个错误的`check_dir`：`/dev/disk/by-path/ip-172.25.134.128%20uid%200:3260-iscsi-iqn.2008-10.org.openstack:f80db967-a8d4-4a05-9443-41b0855f1ec3-lun-1` 
-  没错，就是`portal_address`这个参数，而且经过查找，这个参数就是ironic node中的`driver_internal_info/agent_url`，和我们上一个报错是出自同一个问题源！ 
-  所以不能心存侥幸了，必须要查到这个错误的`agent_url`是从哪里来的了！ 

### 溯源

-  裸机小镜像上的`ironic-python-agent`在启动之后，`ironic_python_agent.agent.IronicPythonAgent.run`会调用`ironic_python_agent.ironic_api_client.lookup_node`方法来调用ironic服务的`/lookup`接口，传入node信息 
-  ironic服务缓存node信息后，在本地开启WSGI，监听9999端口，并调用`ironic_python_agent.IronicPythonAgentHeartbeater.run方法，调用ironic的`/heartbeat`接口，传入`agent_url` 
-  所以，我们在ironic node上看到的错误的host，就是`ironic-python-agent`传进来的。 
> 有关调用的流程，参考：[https://laminar.fun/Openstack/2020-07-19-ironic-deploy.html](https://laminar.fun/Openstack/2020-07-19-ironic-deploy.html)
>  
> 可能根据版本有差异，但大体流程相同

 

-  那么这个`agent_url`是如何获取的？ 
-  当`ironic_python_agent.IronicPythonAgentHeartbeater.run`被调用的时候，会调用`IronicPythonAgent.set_agent_advertise_addr`方法来获取本机IP，也就是`advertise_address`，这个变量将作为`agent_url`的部分被传入`/heartbeat`接口，也就是我们在ironic node上看到的`agent_url`。 
-  `IronicPythonAgent.set_agent_advertise_addr`的定义如下： 
```python
    def set_agent_advertise_addr(self)：
        if self.advertise_address[0] is not None:
            return

        found_ip = None
        if self.network_interface is not None:
            # TODO(dtantsur): deprecate this
            found_ip = hardware.dispatch_to_managers('get_ipv4_addr',
                                                     self.network_interface)
        else:
            url = urlparse.urlparse(self.api_url)
            ironic_host = url.hostname
            # Try resolving it in case it's not an IP address
            try:
                ironic_host = socket.gethostbyname(ironic_host)
            except socket.gaierror:
                LOG.debug('Count not resolve %s, maybe no DNS', ironic_host)

            for attempt in range(self.ip_lookup_attempts):
                found_ip = self._get_route_source(ironic_host)
                if found_ip:
                    break
                time.sleep(self.ip_lookup_sleep)
        if found_ip:
            self.advertise_address = (found_ip,
                                      self.advertise_address[1])
        else:
            raise errors.LookupAgentIPError('Agent could not find a valid IP '
                                            'address.')
```
 

-  这里面的`ironic_host`被传入`_get_route_source`方法来获取IP，而这个变量是通过`api_url`得到的 
-  在启动IPA的时候，`agent.py.run`方法创建了一个`IronicPythonAgent`实例对象，传入了`api_url`这个参数 
```python
def run():
    """Entrypoint for IronicPythonAgent."""
    log.register_options(CONF)
    CONF(args=sys.argv[1:])
    # Debug option comes from oslo.log, allow overriding it via kernel cmdline
    ipa_debug = APARAMS.get('ipa-debug')
    if ipa_debug is not None:
        ipa_debug = strutils.bool_from_string(ipa_debug)
        CONF.set_override('debug', ipa_debug)
    log.setup(CONF, 'ironic-python-agent')
    agent.IronicPythonAgent(CONF.api_url,
                            (CONF.advertise_host, CONF.advertise_port),
                            (CONF.listen_host, CONF.listen_port),
                            CONF.ip_lookup_attempts,
                            CONF.ip_lookup_sleep,
                            CONF.network_interface,
                            CONF.lookup_timeout,
                            CONF.lookup_interval,
                            CONF.driver_name,
                            CONF.standalone).run()
```
 

-  这个参数通过下面这个方法获取 
```python
APARAMS = utils.get_agent_params()
cli_opts = [
    cfg.StrOpt('api_url',
               default=APARAMS.get('ipa-api-url', 'http://127.0.0.1:6385'),
               deprecated_name='api-url',
               help='URL of the Ironic API'),
     ...
]
```
 

-  `utils.get_agent_params()`方法中，定义了获取启动参数的方法 
```python
def get_agent_params():
    # Check if we have the parameters cached
    params = _get_cached_params()
    if not params:
        params = _read_params_from_file('/proc/cmdline')

        # If the node booted over virtual media, the parameters are passed
        # in a text file within the virtual media floppy.
        if params.get('boot_method') == 'vmedia':
            vmedia_params = _get_vmedia_params()
            params.update(vmedia_params)

        # Cache the parameters so that it can be used later on.
        _set_cached_params(params)

    return copy.deepcopy(params)
```
 

-  所以最后，是从`/proc/cmdline`中获取的`api_url`！ 
```bash
# 一个cmdline的例子
initrd=/tftpboot/7dc86606-281c-4851-a3cf-009237117165/deploy_ramdisk selinux=0 disk=cciss/c0d0,sda,sdb,hda,vda iscsi_target_iqn=iqn.2008-10.org.openstack:7dc86606-281c-4851-a3cf-009237117165 deployment_id=7dc86606-281c-4851-a3cf-009237117165 deployment_key=CSA0OQY4DD8VB5CB9AS0G49SRE709PX0 ironic_api_url=http://172.25.134.35:6385 troubleshoot=0 text nofb nomodeset vga=normal console=tty0 console=ttyS0,115200n8 coreos.autologin boot_option=netboot ipa-api-url=http://172.25.134.35:6385 ipa-driver-name=pxe_ipmitool boot_mode=bios coreos.configdrive=0 BOOT_IMAGE=/tftpboot/7dc86606-281c-4851-a3cf-009237117165/deploy_kernel ip=172.25.134.115:172.25.134.35:172.25.128.1:255.255.240.0 BOOTIF=01-28-9e-97-e2-65-65
```
 

-  这个启动参数是ironic节点通过dhcp传入的，作为pxe启动参数，这样整个问题的脉络就清晰了。 
-  回到`IronicPythonAgent.set_agent_advertise_addr`，我们来看`_get_route_source`是如何获取到本机IP的 
```python
    def _get_route_source(self, dest):
        """Get the IP address to send packages to destination."""
        try:
            out, _err = utils.execute('ip', 'route', 'get', dest)
        except (EnvironmentError, processutils.ProcessExecutionError) as e:
            LOG.warning('Cannot get route to host %(dest)s: %(err)s',
                        {'dest': dest, 'err': e})
            return

        try:
            return out.strip().split('\n')[0].split('src')[1].strip()
        except IndexError:
            LOG.warning('No route to host %(dest)s, route record: %(rec)s',
                        {'dest': dest, 'rec': out})
```
 

-  方法调用了`utils.execute`来执行`ip route get <dest>`，而这个dest，就是传入的`ironic_host` 
-  所以我们来看看实际的命令输出 
```bash
> ip route get 172.25.134.35

172.25.134.35 dev enp2s0 src 172.25.134.128 uid 0 
    cache
```
 

-  我们尝试用`out.strip().split('\n')[0].split('src')[1].strip()`来解析，发现这一行没有将最后的`uid 0`过滤，所以才导致返回的IP错误。 
-  经过查找到的资料，发现这个问题在2.0.0版本上已经修改 
```python
# 2.0.0之前的版本
return out.strip().split('\n')[0].split('src')[1].strip()
# 2.0.0
return out.strip().split('\n')[0].split('src')[1].split()[0]
```
 

-  所以，这个问题就很好解决了，我们只需要将这行修改，就可以顺利适配到CentOS9上了。 
