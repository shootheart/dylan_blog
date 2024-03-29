---

title: "docker容器进程用户问题"
date: 2022-08-04T00:00:00+08:00
toc: true
tags: ["docker", "linux"]
categories: ["饭碗"]

---

## 环境

- 宿主机：CentOS7.9
- docker：20.10.9

## 过程

- 在宿主机上部署docker服务并运行一个rabbitmq容器

```bash
docker run -d --hostname rabbitmq02 --name rabbitmq02 -v /var/lib/rabbitmq02:/var/lib/rabbitmq   -v /var/log/rabbitmq02:/var/log/rabbitmq -v /etc/rabbitmq02:/etc/rabbitmq --privileged=True -e RABBITMQ_ERLANG_COOKIE='rabbitmqCookie' rabbitmq:3.10-management
```

- 启动后发现挂载的日志目录无法写入，导致rabbitmq进程退出
- 怀疑是目录权限问题，于是查看了一下映射的/var/lib/rabbitmq02目录

```bash
drwxr-xr-x. 3 polkitd root 63 Sep  8 22:36 /var/lib/rabbitmq02/
```

- 目录的权限居然是polkitd:root！
- 那我直接按这个来修改log目录，再启动容器就可以正常运行了

## 原因

- 从宿主机上查看rabbitmq的进程，也是以polkitd用户运行的

```bash
polkitd   11227  11205  0 Sep08 ?        00:00:00 /bin/sh /opt/rabbitmq/sbin/rabbitmq-server
polkitd   11263  11227  1 Sep08 ?        00:00:55 /usr/local/lib/erlang/erts-13.0.4/bin/beam.smp -W w -MBas ageffcbf -MHas ageffcbf -MBlmbcs 512 -MHlmbcs 512 -MMmcs 30 -P 1048576 -t 5000000 -stbt db -zdbbl 128000 -sbwt none -sbwtdcpu none -sbwtdio none -B i -- -root /usr/local/lib/erlang -bindir /usr/local/lib/erlang/erts-13.0.4/bin -progname erl -- -home /var/lib/rabbitmq -- -pa  -noshell -noinput -s rabbit boot -boot start_sasl -syslog logger [] -syslog syslog_error_logger false -kernel prevent_overlapping_partitions false
```

- 但是在容器里依旧是rabbitmq用户运行

```bash
rabbitmq      1      0  0 15:03 ?        00:00:00 /bin/sh /opt/rabbitmq/sbin/rabbitmq-server
rabbitmq     19      1  1 15:03 ?        00:00:53 /usr/local/lib/erlang/erts-13.0.4/bin/beam.smp -W w -MBas ageffcbf -MHas ageffcbf -MBlmbcs 512 -MHlmbcs 512 -MMmcs 30 -P 1048576 -t 5000000 -stbt db -zdbbl 128000 -sbwt none -sbwtdcpu none -sbwtdio none -B i -- -root /usr/local/lib/erlang -bindir /usr/local/lib/erlang/erts-13.0.4/bin -progname erl -- -home /var/lib/rabbitmq -- -pa  -noshell -noinput -s rabbit boot -boot start_sasl -syslog logger [] -syslog syslog_error_logger false -kernel prevent_overlapping_partitions false
```

- 所以问题的原因，只是容器里rabbitmq的uid在宿主机上对应的是polkitd这个用户而已

```bash
# 容器
root@rabbitmq02:/# id rabbitmq
uid=999(rabbitmq) gid=999(rabbitmq) groups=999(rabbitmq)

# 宿主机
[root@localhost log]# id polkitd
uid=999(polkitd) gid=998(polkitd) groups=998(polkitd)
```
