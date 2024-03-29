---
title: "家用HTPC方案v1.0"
date: 2017-11-03T00:00:00+08:00
draft: false
toc: true
tags: ["媒体中心"]
categories: ["生活"]
---


> HTPC（Home Theater Personal Computer），即家庭影院电脑。 是以计算机担当信号源和控制的家庭影院，也就是一部预装了各种多媒体解码播放软件，可用来对应播放各种影音媒体，并具有各种接口，可与多种显示设备如电视机、投影机、等离子显示器、音频解码器、音频放大器等音频数字设备连接使用的个人电脑。


## 之前使用树莓派的方案与局限性

之前因为手头有闲置树莓派所以暂时将其作为pt下载机，并由此做出搭建家用HTPC的临时方案。

临时方案很简单，树莓派主要任务为pt下载，之后连接带电源的硬盘盒作为文件存储服务器，电视通过内网连接并读取文件或播放视频。

由此可见该方案的**局限性**：
* 树莓派功耗较低，但是通过usb无法带起大硬盘正常工作，需要硬盘独立供电。
* 树莓派自身cpu与内存空间有限，在后台运行大量进程后资源吃紧。
* 由于剩余资源较少，无法再额外提供高清视频解码功能。
* 树莓派无法解码视频，电视只能通过内网传输并自身解码播放视频，因此很受网络速率与自身解码器性能的影响（*树莓派不支持h265高清视频*）。

因此，当使用需求增多后，该临时方案将不能满足。需搭建性能强，耗电少，可扩展性高的HTPC主机。

## 需求
* 支持各种常见媒体格式的解码播放，支持h265硬解码，甚至4K视频播放。
* 有足够空间安装3.5寸台式机大硬盘，可以存储大量文件并通过局域网共享。
* 主机需直接通过HDMI线连接到客厅电视，以避免局域网速率限制视频流传输。
* 要求操作界面简洁方便，容易上手。
* 可以保证长期稳定运行而且耗电量低。
* 支持bt下载与迅雷下载。
* 支持内外网环境下远程管理。
* 主机体积足够小，可以随意放置。

> 可选：游戏需求，可以流畅运行一些非大型游戏。

## 方案设计

### 硬件方面

>对于如今家用HTPC的搭建方案，已经有很多比较完善的例子，不过还是要根据自身需求来选择硬件。

* **主板及处理器**

  **华擎科技 J3455-ITX：539RMB**

  在现有的例子中，intel推出的新一代赛扬处理器是最为用户津津乐道的，因为他具备了低功耗与高性能的特点，其自带的核心显卡可以完美硬解h265甚至4K视频，无疑是现阶段最好的选择。有数家主板厂商推出了集成该处理器的ITX迷你主板，接口功能齐全，价格也适中。

* **内存**

  **金士顿KVR16LS11/4 KST 4G DDR3 1600L（二手）：145RMB**

  华擎科技的官方网站上提供了J3455-ITX主板所支持的内存型号（*有很多网友吐槽其内存兼容性，其实并不是主板兼容问题，而是处理器的问题*），所以在考虑到现今内存条价格疯涨的特殊情况，决定使用二手内存条，可以节省近50元。

* **硬盘**

  **士必得 M3-32G固态硬盘（附带数据线与台式机托架）：106RMB**

  SSD固态硬盘，用来做系统盘，既然需求不高也无需买高端产品，满足日常使用即可。

* **机箱**

  **祐泽海洋之星+标配1U电源250W：135RMB**

  在所有物品中，机箱是找的时间最长的，因为个人原因，第一不喜欢机箱体积过小导致使用DC外置电源，第二不喜欢体积过大像一般台式机一样的，第三考虑到预算决定将机箱价格控制在200以内，所以放弃了之前最中意的乔思伯品牌（*个人认为乔思伯的外观是最好的，大小也可以接受，只是价格偏高*）。最后决定用海洋之星，这机箱应该是价格最便宜的了，由于体积原因只能使用服务器1U电源，不过还好内部空间足够大，还特意向卖家请教了一些空间利用的方法。

**<font color="red">硬件预算总计（不包括其他配件）：930RMB</font>**

### 软件方面

> 硬件的性能固然重要，但是用户体验更重要，因此软件方面必须做到界面友好，操作简单，尽量让用户体验做到最好。

* **操作系统**

  **Lubuntu 16.04LTS**

  操作系统第一个不会考虑windows，虽然在软件兼容性和用户界面上win比较好，但是会带来高占用资源和各种垃圾软件病毒的问题，所以还是选择用基于Linux的系统，也方便远程控制。Ubuntu是再熟悉不过的系统了，使用LXDE轻量级桌面在资源占用上会更低。
  
  > 主板说明书上只标明Linux操作系统支持Ubuntu 16.10，之后要具体测试一下。

  > **2017-11-12更新：事实证明，Ubuntu近期的版本（目前只试过LXDE和Unity桌面），在安装上之后无法通过HDMI接口输出声音，各种软件设置均无效，这种情况同样发生在Debian（Xfce桌面）系统上。目前Windows10和Fedora（Gnome桌面）测试无问题（*或为桌面环境导致*），而且在Windows10环境下资源占用较高，因此暂时使用Fedora系统，有待进一步观察是否出现问题。**

  > **2017-11-26更新：上述问题已排查，因为之前测试Kodi环境下插移动硬盘不能自动挂载（需要添加自动挂载策略），所以为了方便就在fstab文件中添加了开机自动挂载移动硬盘的条目，但是如果开机检查该文件发现硬盘没有连接，将无法正常启动系统，也就是上述问题的所在，所以删除该条目就可以解决。**

* **媒体中心**

  **Kodi v17.5 "Krypton"**

  作为一款开源媒体中心项目，可以说Kodi已经集成了所有你可能想到的功能，支持所有平台，而且提供了强大的可扩展的插件库，可以自己制作也可以使用他人制作的插件来实现各种功能。而且对媒体格式的支持也是很完美，支持媒体信息搜刮器，个人觉得是搭建个人媒体库的不二选择。

  *由于Kodi基于Ubuntu的KODIbuntu系统貌似已经停止更新，所以选择以软件形式安装。*

  > 虽然Kodi的插件功能很强，但是中文插件资源依然很少，其中一方面原因也是因为源网站对其的封堵，导致很多插件已经失效并停止更新。

* **其他软件**

  基础操作系统为Linux，所以在这里使用SSH进行远程操作，Samba服务负责局域网文件共享，n2n负责内网穿透方便外网远程控制，Deluge进程负责pt下载。

  > 如果有需求，可以使用虚拟机安装windows，方便使用迅雷下载或其他需要win平台的软件。
  
## 方案实施

> 方案已经确定，理论上没有太多问题，但是在实施的过程中，会因为各种因素导致过程不顺利，因此在实施的过程中将会有许多问题待解决。

### 硬件方面

硬件方面无太多变动，安装过程也没有太多阻碍，只是机箱的空间与预计较为不同，原本计划在其他硬件安装完毕之后还可以在机箱侧壁以两颗螺丝固定一块3.5寸大硬盘，但实际测量发现cpu散热片超过预想的高度，导致剩余空间可能不足以放下一块大硬盘。

对于固态硬盘的安放也与预期相差较多，机箱顶盖有固定固态硬盘的位置，但是考虑到过后还要在那个地方安放其他硬盘所以决定将其放入电源下面的空间里，然而固态硬盘配套的螺丝根本不符合其自身螺丝孔，而且机箱侧面的圆形散热孔不能完美对上硬盘侧面的两个螺丝孔，所以只能更换其他螺丝并且使其中一颗螺丝斜着拧入。

机箱散热风扇由于没有测量顶盖的风扇位置大小而错买了，尝试过用双面胶粘贴，但发现使用一段时间会掉，所以只能用一颗螺丝固定在顶盖上，还好效果没有那么差。

其他硬件并没有发现兼容问题，一次性点亮，只是连接我的便携式显示器的时候**必须用一根充电线把显示器和机箱连接起来才不会有问题**，使用外接电源就是不亮，有可能与机箱漏电有关，希望接到电视上不会出现此问题。

### 软件方面

实施过程最让人头疼的就是软件问题，对于Linux系统来说，兼容问题远比Windows系统多的多（尤其对这种较新的硬件，主板说明书上也标明**推荐Windows10**）。

首先是按照原方案中提到的Ubuntu（LXDE桌面），安装上后并没有发现有其他问题，但是在kodi安装上之后测试才发现HDMI无法输出声音，在网上也有很多教程解决此问题，但是均不起作用。其一，教程中大多是对于Ubuntu原版系统，会导致桌面环境影响；其二，很有可能是因为操作系统对该硬件存在兼容问题。

> **2017-11-26更新：对于HDMI声音输出问题，目前决定暂时放弃。**

之后在尝试过其他版本的Lubuntu后决定暂时放弃该系统，同时也断定是系统的问题，那么就按照主板说明书上提到的Fedora 25系统来测试，没想到这个系统就没有声音输出的问题了，而且其使用的Wayland显示服务器比传统的X服务器更顺畅，只不过相对资源占用较大（但还是甩win10几条街）。

> Fedora系统安装Kodi与Debian系的完全不一样，不过Fedora使用的源包含的组件更加全面，不需额外下载其他组建。安装完Kodi之后在登录桌面环境中都有一个单独的Kodi环境，也就是不需依赖其他桌面环境运行，相对更省资源。

不过Fedora系统之后也出现了问题，在一次测试中播放视频突然黑屏，显示器忽亮忽暗，而且只要退出Kodi全屏播放模式就恢复了（此问题是在单独Kodi环境下，也就是standalone环境下发生的），之后尝试过更改显示屏刷新率但是没有效果，不过发现只要将输出模式改为1920X1080i就恢复正常了。**还要说明一点，在Gnome环境下运行Kodi不会出现此问题。**

期间也尝试过Debian（Xfce桌面），Ubuntu16.04，Windows10。Debian就和Ubuntu一样了，都存在没有声音的问题，不过不得不说win10是问题最少的，但是使用win10的话就面临三个问题：未必永久激活，资源占用大，远程控制困难。所以现在还是选择拯救者Fedora。

> **2017-11-26更新：系统方面最终决定使用Ubuntu。**

对于Kodi的设置就没有过多想说的了，怎么使用舒服简单就怎么设置，而且Kodi使用手机遥控还是很好用的，感觉真的是开箱即用。

## 总结

个人来说算是第一次完整装机，从查阅资料到选择配置再到组装和系统调试，大概断断续续花费了一个多月的时间。有时候对于方案的设计还是存在很多欠考虑的地方，比如这次机箱空间的计算，还有系统方面的各种问题。。也可能因为这次装机用途比较特殊，毕竟不是主流电脑配置，所以有很多地方无法找到有用的资料，而且也预计不到结果如何，导致过程中会出现种种问题，不得不说弄起来真的很累。。

不过有些时候学习就是一些事情逼出来的，装机过程还是可以学到很多东西的，还要注意很多细节。装机也是门手艺，弄好了也是很了不起的哦~

估计接下来我又要折腾一台迷你主机了，真的会上瘾的。。
