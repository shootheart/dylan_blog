---
id: 埋了五年的雷终于爆了-2025-06-04
aliases: 
tags:
  - Linux
  - Nas
title: 埋了五年的雷终于爆了
date: 2025-06-04T00:00:00+08:00
lastmod: 2025-06-04T00:00:00+08:00
draft: false
toc: true
categories:
  - 生活
hiddenFromHomePage: false
hiddenFromSearch: false
---


## 起因

最近在折腾新Nas准备做AIO，所有的服务都用pve的lxc运行，旁路由也不例外。

为了刮削电影数据方便，我还装了一个tinymediamanager，网关指向旁路由方便连接数据源网站。

结果测试刮削的时候翻车了，怎么都连不上TMDB的api。dns也是指向的旁路由，测试了dns解析也没问题，但是旁路由日志上根本没看到这个服务发来的包。

因为还有其他lxc也是同样的网络配置，我也测试了一下，都是TMDB的首页能访问，api就不可以。。。

## 排查

折腾了几个小时后，我突然发现是不是防火墙的问题，因为我的笔记本是设置的主路由然后dns是旁路由，在笔记本上测试就可以正常访问。

然后我发现了这个api域名解析出的地址：

```
Non-authoritative answer:
Name:   api.themoviedb.org
Address: 3.169.231.116
Name:   api.themoviedb.org
Address: 3.169.231.119
Name:   api.themoviedb.org
Address: 3.169.231.17
Name:   api.themoviedb.org
Address: 3.169.231.97
```

然后我的旁路由上防火墙有这么一条：

```
        chain prerouting {
                type filter hook prerouting priority filter; policy accept;
                ip daddr { 0.0.0.0/4, 127.0.0.1, 172.16.0.0/15, 224.0.0.0/4, 255.255.255.255 } return
                           ^ ^ ^ ^ ^
        }
```

`0.0.0.0/4`这个网段居然被我过滤掉了！

## 吐槽

旁路由的所有配置文件都是从老的机器上直接拷贝来的，也就是说这个问题**埋了差不多五年**才被我发现。。。

我已经记不清为什么要加这个网段了，因为透明代理的社区指导文档上也没有提到这么加，大概是我一时脑残错把A类IP段写上了，但是A类IP地址也不是这么写，保留地址段也不是这么写。。。真奇怪！

> A类网络：范围从1.0.0.0到127.0.0.0，网络地址的最高位必须是“0”，可用的A类网络有127个，每个网络能容纳16777214个主机。其中127.0.0.1是一个特殊的IP地址，表示主机本身，用于本地机器的测试。
> B类网络：范围从128.0.0.0到191.255.255.255，网络地址的最高位必须是“10”，可用的B类网络有16382个，每个网络能容纳6万多个主机。
> C类网络：范围从192.0.0.0到223.255.255.255，网络地址的最高位必须是“110”，C类地址是由3个字节的网络地址和1个字节的主机地址组成。
> D类网络：D类地址用于多播（组播）通信，范围是224-239。D类地址没有具体的保留网段，用于指定多播组的地址。
> E类网络：E类地址是保留给特殊用途的地址，范围是240-255。E类地址同样没有具体的保留网段，被保留供未来使用。
