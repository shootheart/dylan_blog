---
title: "vsftpd学习"
date: 2018-02-25T00:00:00+08:00
draft: false
toc: true
tags: ["ftp","linux"]
categories: ["饭碗"]
---

学习Linux运维的过程中，对于一些常见的服务的搭建是必不可少的，FTP是我们经常使用的文件传输协议，在Linux上我们用vsftpd来搭建FTP服务器。

## 安装

安装自然不必多说，在RHEL上使用yum可以轻松安装该软件。

为了测试过程中不会因为防火墙阻挡而影响结果，可以先清空防火墙的规则。

在vsftpd的配置文件里已经有了大多数的常见配置，并对相关语句做了注释，因此对于平常使用来说可以很容易的实现。

下面我们尝试用匿名登录FTP服务器。

## 登录

需要修改的配置有以下几条：

1 anonymous_enable=YES

2 anon_umask=022

3 anon_upload_enable=YES

4 anon_mkdir_write_enable=YES

5 anon_other_write_enable=YES

> 注意：每次修改完配置后都需要重启vsftpd服务才能生效。

配置保存，重启服务后，可以在本机上使用ftp登录（配置中的local_enable表示是否允许本机登录），在输入用户名的时候选择anonymous，密码为空。

此时可以登录成功，但是无法创建目录，原因为匿名登录的默认目录为/var/ftp/，通过查看目录我们可以发现，该目录的所有者和群组都是root，而我们需要将所有者改为
ftp才能有该目录的写权限，所以使用chown修改目录所有者。

此时再使用ftp尝试匿名登录，发现报错：

500 OOPS: vsftpd: refusing to run with writable root inside chroot()

Login failed.

421 Service not available, remote server has closed connection

## 分析报错并解决

对于此报错，是chroot的策略导致的，在配置文件的注释中也有讲解：

 You may specify an explicit list of local users to chroot() to their home
 directory. If chroot_local_user is YES, then this list becomes a list of
 users to NOT chroot().
 (Warning! chroot'ing can be very dangerous. If using chroot, make sure that
 the user does not have write access to the top level directory within the
 chroot)

FTP中有chroot功能，意思是在用不同的用户登录的时候访问目录将限制在该用户的家目录中，也就是除了用户的家目录不能访问其他目录，但是使用该功能的前提是用户
不能对自己的家目录有写权限，这也是上面报错的原因（/var/ftp的权限为755）。

因此，只要将/var/ftp的权限改为555或将该目录的所有者改为root，之后在二级目录中操作文件的增删改查就可以了。

> 对于anonymous来说，任何情况下都开启chroot。

## chroot的探索

chroot功能可以使用chroot_local_user语句来开启或关闭（针对所有有权限登录的本地用户），除此之外，也可以在关闭的状态下使用chroot_list_enable来选择为哪些用
开启。

> 正如配置说明中所说，当chroot为关闭状态下，设置list可以实现为用户单独开启chroot，而在chroot开启的状态下，设置list就变成了为用户单独取消chroot。

虽然软件在这方面做了严格限定，但是要取消家目录的写权限实在是不方便，所以配置中还给出了一条语句allow_writeable_chroot，将其设置为YES，就可以在用户对
其家目录保留写权限的情况下使用chroot。

 
