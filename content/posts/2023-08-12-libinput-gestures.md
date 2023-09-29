---
title: "利用libinput-gestures让触控板手势更丰富"
date: 2023-08-12T00:00:00+08:00
lastmod: 2023-08-12T00:00:00+08:00
draft: false
toc: true
tags: ["Linux", "Arch"]
categories: ["生活"]
hiddenFromHomePage: false
hiddenFromSearch: false
---

## 关于libinput-gestures

> [Arch Wiki对于libinput-gesture的说明](https://wiki.archlinuxcn.org/wiki/Libinput?rdfrom=https%3A%2F%2Fwiki.archlinux.org%2Findex.php%3Ftitle%3DLibinput_%28%25E7%25AE%2580%25E4%25BD%2593%25E4%25B8%25AD%25E6%2596%2587%29%26redirect%3Dno#libinput-gestures)
>
> [libinput-gestures的Github主页](https://github.com/bulletmark/libinput-gestures)

`libinput-gestures`是为`linux`下触控板提供自定义手势配置的程序。

`libinput`已经对触控板的基本使用手势有了支持，有部分DE和WM已经支持定义一些手势（比如`Gnome`、`KDE`），但是并不一定能够覆盖所有，并且一般都是已经预设好的，不支持自定义。

所以可以通过使用`libinput-gestures`程序来扩展触控板的使用。

## 安装

`Arch Linux`可以通过AUR仓库安装：

```bash
$ yay -S libinput-gestures
```

`libinput-gestures`还可以搭配`wmctrl`和`xdotool`两个工具来扩展手势定义的动作：

```bash
$ pacman -S wmctrl xdotool
```

## 启动

`libinput-gestures`的启动方式有两种，`systemd service`方式和`desktop application`方式，通过`libinput-gestures-setup`命令来指定启动方式或者是否自启动。

我们使用`systemd`方式作为user服务来启动：`libinput-gestures-setup service`

这里可能会出现“Systemd not available, can not run as service.”的错误提示，这是因为`libinput-gestures.service`中的`[Install]`是`graphical-session.target`，而我们在user环境下使用的是`default.target`，`libinput-gestures-setup`脚本无法检测到对应的`target`，所以设置失败。

我的解决方法是：

1. 将`libinput-gestures.service`中的所有`graphical-session.target`修改为`default.target`

   ```bash
   # /home/dylan/.config/systemd/user/libinput-gestures.service
   [Unit]
   Description=Actions gestures on your touchpad using libinput
   Documentation=https://github.com/bulletmark/libinput-gestures
   PartOf=default.target  # <-- 修改
   After=default.target   # <-- 修改
   
   [Service]
   Type=simple
   ExecStart=/usr/bin/libinput-gestures
   
   [Install]
   WantedBy=default.target  # <-- 修改
   ```

2. `libinput-gestures-setup`脚本中关于`HAS_SYSD`的检测也改为`default.target`

   ```bash
   # /usr/bin/libinput-gestures-setup
   ...
   	# Test if systemd is installed
       if type systemctl &>/dev/null; then
           #HAS_SYSD=$(sysd_prop graphical-session.target ActiveState active)  # <-- 注释，改为下面这行
           HAS_SYSD=$(sysd_prop default.target ActiveState active)
       else
           HAS_SYSD=0
       fi
   ...
   ```

   > 这不是最好的办法，可能在`libinput-gestures`更新后被覆盖

设置为`service`方式之后，设置为自动启动：`libinput-gestures-setup autostart`

立即开启`libinput-gestures-setup start`

## 配置

软件默认的配置文件为`/etc/libinput-gestures.conf`，可以通过`~/.config/libinput-gestures.conf`来创建用户配置。

**因为我使用`XFCE`，在窗口管理器中配置好快捷键，之后可以通过`xdotool`映射到gestures。**

下面以我的配置文件为例：

```bash
# 3 finger swipe
gesture swipe up			3 xdotool key control+1 # 切换到工作区1
gesture swipe down			3 xdotool key control+2 # 切换到工作区2
gesture swipe left_up		3 xdotool key alt+Left  # 后退操作
gesture swipe right_up		3 xdotool key alt+Right # 前进操作
gesture swipe right			3 xdotool key control+Tab        # 上一个Tab
gesture swipe left			3 xdotool key control+shift+Tab  # 下一个Tab

# 4 finger swipe
gesture swipe up			4 xdotool key super+Up       # 窗口最大化
gesture swipe down			4 xdotool key super+Down     # 窗口最小化
gesture swipe left			4 xdotool key super+Left     # 窗口置左
gesture swipe right			4 xdotool key super+Right    # 窗口置右
gesture swipe left_up		4 xdotool key super+Page_Up  # 窗口置左上
gesture swipe left_down		4 xdotool key super+Home     # 窗口置左下
gesture swipe right_up		4 xdotool key super+Page_Down# 窗口置右上
gesture swipe right_down	4 xdotool key super+End      # 窗口置右下

# 2 finger pinch
gesture pinch clockwise		2 xdotool key alt+Tab        # 顺时针向前切换窗口
gesture pinch anticlockwise	2 xdotool key alt+shift+Tab  # 逆时针向后切换窗口

# hold on gestures
gesture hold on				4 xdotool key control+F4  # 四指按住关闭当前页
gesture hold on				3 xdotool key alt+F8      # 三指按住调整窗口大小
#gesture hold on				2 xdotool key alt+F7

# pinch in/out
gesture pinch in			xdotool key ctrl+KP_Subtract # 两指捏缩小
gesture pinch out			xdotool key ctrl+KP_Add      # 两指扩放大

# device
device all   # 所有设备均应用
```

> 关于device选项*这里做个记录：*
>
> 先前我没有仔细查看libinput-gestures.conf对于设备选择的说明，只对手势定义做了配置；
>
> 实际使用时笔记本和外接触控板同时只能有一个对手势生效，如果我的外接触控板断开，内置的触控板不会接替生效，必须重启服务；
>
> 于是我准备在udev rule中对触控板的连接与断开事件指定一个重启服务的操作；
>
> 但无奈如果使用desktop方式启动libinput-gestures，udev rule在执行RUN脚本时会出现很多问题（比如X环境变量、执行用户等），并且也无法直接利用restart命令；
>
> 最后我换成service启动，并且在rule中配置了对服务的依赖，才勉强实现了切换；
>
> 实际上libinput-gestures可以指定某个device，甚至是监听所有的devices；
>
> 没有仔细查看文档导致绕了这么一个大弯路，谨此作为教训。

## 调试

使用`libinput-gestures -d`对已定义好的手势进行调试。

**注意要将已经运行的`libinput-gestures`程序关闭。**