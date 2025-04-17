---
title: "systemd-nspawn运行docker-2025-04-17"
date: "2025-04-17T12:21"
lastmod: "2025-04-17T12:21"
tags:
  - Linux
  - 容器
---

## 环境

Arch Linux

## docker启动问题

之前使用`systemd-nspawn -b -D path`这种方式运行容器，如果直接安装启动docker，会出现如下的报错导致无法启动
```
Apr 17 10:01:53 dylanarch systemd[1]: docker.service: Main process exited, code=exited, status=1/FAILURE
Apr 17 10:01:53 dylanarch systemd[1]: docker.service: Failed with result 'exit-code'.
Apr 17 10:01:53 dylanarch systemd[1]: Failed to start Docker Application Container Engine.
Apr 17 10:01:55 dylanarch systemd[1]: docker.service: Scheduled restart job, restart counter is at 1.
Apr 17 10:01:55 dylanarch systemd[1]: Starting Docker Application Container Engine...
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.695447082+08:00" level=info msg="Starting up"
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.695890718+08:00" level=info msg="OTEL tracing is not configured, using no-op tracer provider"
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.705906475+08:00" level=info msg="Creating a containerd client" address=/run/containerd/containerd.sock timeout=1m0s
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.748511332+08:00" level=info msg="[graphdriver] using prior storage driver: overlay2"
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.749921301+08:00" level=info msg="Loading containers: start."
Apr 17 10:01:55 dylanarch dockerd[149]: time="2025-04-17T10:01:55.774357608+08:00" level=info msg="stopping event stream following graceful shutdown" error="<nil>" module=libcontainerd namespace=moby
Apr 17 10:01:55 dylanarch dockerd[149]: failed to start daemon: Error initializing network controller: error obtaining controller instance: failed to register "bridge" driver: failed to create NAT chain DOCKER: iptables failed: iptables --wait -t nat -N DOCKER: iptables v1.8.11 (legacy): can't initialize iptables table `nat': Permission denied (you must be root)
Apr 17 10:01:55 dylanarch dockerd[149]: Perhaps iptables or your kernel needs to be upgraded.
```

### 如何配置容器启动

根据[依云博客](https://blog.lilydjwg.me/2023/6/29/nspawn-docker.216651.html)记录的，可以添加`SYSTEMD_SECCOMP=0`这个变量将nspawn的权限限制去掉来解除容器嵌套问题。

但是感觉全部取消限制似乎太粗暴了，应该还有更好的方案。

按[Arch Wiki](https://wiki.archlinuxcn.org/wiki/Systemd-nspawn#%E5%9C%A8_systemd-nspawn_%E4%B8%AD%E8%BF%90%E8%A1%8C_docker)中描述的，新版的docker已经可以通过修改配置使其在无特权systemd-nspawn容器下运行了，虽然也会暴露一些系统调用，但安全性还是有一定保障的。

但是按照wiki中的进行配置之后，依旧会出现iptables这个报错。其实从报错中看，似乎和某个网络设备的权限有关。

### 如何配置网络

我们之前使用的命令，是全部使用主机网络启动容器，docker无法启动的话，可能是因为某个网络设备无法访问。

那可以尝试使用私有网络，桥接到主机的网卡上。

`systemd-nspawn --network-bridge=virbr1 -bD path`

尝试开启容器，给容器的虚拟网卡配置IP，运行docker是正常的了。

## 运行docker容器的错误

```
Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: error mounting "sysfs" to rootfs at "/sys": mount src=sysfs, dst=/sys, dstFd=/proc/thread-self/fd/8, flags=0xf: operation not permitted
```

这个问题似乎还没有真正解决，[github上提到的这个方法](https://github.com/systemd/systemd/issues/27994#issuecomment-1704005670)是有效的。

`systemd-nspawn --network-bridge=virbr1 --bind=/proc:/run/proc --bind=/sys:/run/sys -UbD path`
