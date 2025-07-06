---
title: 为NAS配置UPS及断电自动关机
date: 2025-07-06T00:00:00+08:00
lastmod: 2025-07-06T00:00:00+08:00
draft: false
toc: true
tags:
  - Linux
  - NAS
categories:
  - 生活
hiddenFromHomePage: false
hiddenFromSearch: false
---
## 架构

购买的是山特 TG-BOX 850，这个型号支持 USB 连接设备从而实现断电自动关机的功能。

NAS 目前使用的是 PVE（基于 Debian 系统），关于 Linux 系统与 UPS 的集成，选择的是 [NUT]() 项目。老牌的开源 UPS 管理软件，而且目前还在活跃开发中，相比 [apcupsd]()，似乎使用的人更多。

## 安装

Debian 系统可以直接从软件源中安装：`apt update && apt install -y nut`

## 配置 NUT 服务

根据手册的说明，NUT 可以通过 USB、串口、网络等方式来连接 UPS 设备，可支持多种架构灵活配置，不过由于我们只有一台设备加一台 UPS，所以使用最简单也是最普遍的架构，也称为 [“Standalone”](https://networkupstools.org/features.html#:~:text=%22Simple%22%20configuration)架构。最小配置为：一个 Driver 配置、一个 upsd 进程和一个 upsmon 进程。

[Debian Wiki](https://wiki.debian.org/nut) 描述：

> 阅读 `/etc/nut/nut.conf`，然后指定你要使用 NUT 的计划：
> `MODE=standalone`

按照这个修改 `/etc/nut/nut.conf` 文件。
### Driver 配置

要使用 UPS 设备，首先我们需要根据 UPS 设备的连接方式进行驱动的配置，NUT 很贴心地提供了 [`nut-scanner`](https://networkupstools.org/docs/man/nut-scanner.html) 工具为用户自动发现可用的 UPS 设备并生成对应的 `ups.conf` 配置文件。我们这里使用的是 USB 连接，所以可以执行 `nut-scanner -U > /etc/nut/ups.conf` 来生成这个驱动配置。之后可以修改驱动配置的名称。

`ups.conf` 中包含密码，记得修改文件所属 `root:nut` 与文件权限 `640`。
### 启动 nut 服务

重启 NUT 服务端：

`systemctl restart nut-server.service`

`nut-driver-enmuerator.path` 是监听驱动配置目录的，我们生成了一个新的驱动配置，它将调用 `nut-driver-enmuerator.sh` 来生成一个对应驱动的 service 实例。

### 验证UPS连接

可以使用下面的命令验证 UPS 的可用性。下面命令的名称参数，就是上面 `ups.conf` 里写的驱动配置名称。

查看 UPS 可用的命令：

`upscmd -l eaton850`

查看 UPS 的信息数据：

`upsc eaton850`

### 配置 upsd

编辑 `/etc/nut/upsd.user` 来配置 `upsd` 的访问权限：

```ini
[admin]
        password = some_complex_password
        actions = SET
        instcmds = ALL
		upsmon primary
```

编辑 `/etc/nut/upsmon.conf` 来配置 UPS 的监控：

```ini
...
#       UPS名称  upsd服务器 电源数 用户  密码                   角色类型
MONITOR eaton850@localhost 1 admin some_complex_password primary
...
```

重启 NUT 服务

`systemctl restart nut-server.service`

`systemctl restart nut-monitor.service`

至此已完成与 UPS 的通信。

## 实现低电量自动关机

`NUT` 实现 UPS 低电量自动关机是通过 `upsmon` 监控电源事件，当检测到 UPS 电量即将耗尽（LOWBATT）时，会产生 NOTIFY_SHUTDOWN 事件，之后执行关机命令。

### 配置 upsmon

关机命令在 `upsmon.conf` 中进行定义：

```ini
...
SHUTDOWNCMD "/sbin/shutdown -h +0"
...
# 关机前的延迟时间
FINALDELAY 5
...
# 电源事件的FLAG
NOTIFYFLAG ONLINE     SYSLOG+WALL
NOTIFYFLAG ONBATT     SYSLOG+WALL
NOTIFYFLAG LOWBATT    SYSLOG+WALL
...
# 可自定义消息推送的命令
NOTIFYCMD /bin/notifyme
...
```

重启 `upsmon` 服务：

`systemctl restart nut-monitor.service`

## 验证

关闭 UPS 的市电电源，绿灯闪烁，蜂鸣器每 2s 响一次，证明电池正常供电。`nut-monitor` 服务接收到消息：

```
Jul 06 14:32:38 Nas nut-monitor[3281]: UPS eaton850@localhost on battery
```

当 UPS 剩余电量不足 20%，`nut-monitor` 接收到电量不足的消息，开始执行关机操作：

```
Jul 06 15:26:09 Nas nut-monitor[3281]: UPS eaton850@localhost battery is low
Jul 06 15:26:09 Nas nut-monitor[3281]: Executing automatic power-fail shutdown
Jul 06 15:26:09 Nas nut-monitor[3281]: Auto logout and shutdown proceeding
```

## 关机的额外操作

实际上 PVE 服务器的关机操作不需要额外的操作，在正常的 `shutdown` 过程中会自动尝试关闭所有的虚拟机/容器，同时 zfs pool 也不需要执行额外的卸载命令，操作系统在关闭的过程中会自动进行处理。 

> https://www.reddit.com/r/Proxmox/comments/st7i6j/do_i_need_to_do_anything_special_to_shutdown/
> https://forums.freebsd.org/threads/safe-and-clean-shutdown-with-zfs.45498/