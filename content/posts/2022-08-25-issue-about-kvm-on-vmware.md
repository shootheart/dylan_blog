---

title: "vmware部署kvm无法启动云主机"
date: 2022-08-25T00:00:00+08:00
toc: true
tags: ["虚拟化"]
categories: ["饭碗"]

---

## 问题

- 在vmware环境部署zstack all in one环境，创建虚拟机之后无法启动，只显示seabios的信息，无法进入系统
- 更换硬盘的接口模式无效

## 解决

-  vmware对于kvm虚拟化的支持不太好，需要对内核模块做些修改 
-  首先将开启的虚拟机全部关闭 
-  编辑`/etc/modprobe.d/kvm-nested.conf`，在最后添加`ept=0`: 
```bash
options kvm_intel nested=1 ept=0
```
 

-  然后重新加载kvm模块 
```bash
rmmod kvm-intel
## 卸载kvm_intel模块
modprobe kvm-intel ept=0 unrestricted_guest=0
## 安装kvm_intel模块
```
 

-  重启云主机，就可以正常进入了 
