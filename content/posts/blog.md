---

title: "测试文章"
date: 2021-12-29T00:00:00+08:00
toc: true
tags: ["web"]
categories: ["技术"]

---

### nmcli自定义网桥

```bash
> nmcli con add type bridge ifname br-user con-name br0 # 新建网桥
> nmcli con add type bridge-slave ifname eth0 master br0 # 添加端口
> nmcli con modify br0 bridge.stp no # 禁用stp

> nmcli con down "Wired connection 1" # 关闭eth0的连接
> nmcli con up br0 # 开启网桥

# 通过dhcp获取ip，没有手动配置
```

### ~~将自定义网桥加入virsh~~

```bash
> cat /tmp/br-lc.xml  # 编辑配置
<network>
  <name>br-lc</name>
  <forward mode='route'/>
  <bridge name='br-lc' stp='on' delay='0'/>
  <ip address='192.168.56.101' netmask='255.255.255.0'>
  </ip>
</network>

> virsh net-define /tmp/br-lc.xml
> virsh net-start br-lc
```

> `virsh net-start`会在`NetworkManager`中自动创建一个该网桥的连接，如果之前在nmcli中已经创建了一个连接，会产生冲突并出现如下报错：
>  
> `internal error: Network is already in use by interface br-lc`
>  
> libvritd: 4.5.0-36


> 如果创建的是直连网络，可以不用这种方式，直接创建好网桥，在创建虚机时指定连接到该网桥上


### qemu-kvm启动虚拟机无法设定自定义网桥

```bash
# 启动参数
-netdev bridge,id=net1,br=br-lc -device virtio-net,netdev=net1

# 错误信息
access denied by acl file
qemu-kvm: bridge helper failed

# 在/etc/qemu-kvm/bridge.conf中添加自定义网桥
allow virbr0
allow br-lc
```

> 利用libvirtd启动虚机，不存在此类问题


### 调用

libvirtd -> qemu -> kvm

> [Virtualization and Hypervisors :: Explaining QEMU, KVM, and Libvirt | Sumit’s Dreams of Electric Sheeps](https://sumit-ghosh.com/articles/virtualization-hypervisors-explaining-qemu-kvm-libvirt/)


### libvirt网络手册

> [https://jamielinux.com/docs/libvirt-networking-handbook/index.html](https://jamielinux.com/docs/libvirt-networking-handbook/index.html)

{{< music auto='https://music.163.com/outchain/player?type=2&id=212645&auto=0&height=66' >}}


<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1670835931407-2574716b-7d82-421c-b1de-e84346471d1f.png" alt="图片.png" referrerPolicy="no-referrer" />


