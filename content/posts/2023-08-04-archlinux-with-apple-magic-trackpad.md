---
title: "如何在Arch Linux下优雅地使用Apple Magic Trackpad"
date: 2023-08-04T00:00:00+08:00
draft: false
toc: true
tags: ["Linux", "Arch", "Apple"]
categories: ["生活"]
---

## 前言

+ 我的办公环境，是将笔记本架起来当作副屏使用，外接的显示器当作主屏，这样就需要外接键盘与鼠标。
+ 先前使用libinput-gestures组件实现了对thinkpad触控板的手势开发，本着避免鼠标手的（装逼）想法，我觉得要放弃鼠标，拥抱触控板。

## 选择哪种触控板

+ 现在市面上可选的外接触控板大概有下面几种：

  + **Apple Magic Trackpad**：

    Apple这款是公认的好用，配合Apple全家桶简直无可挑剔；windows上可能[设置会比较麻烦](https://opnir.cn/2020/07/using-apple-magic-trackpad-on-windows-pc.html)，并且手势貌似也并不丰富，但好在linux上可以直接使用，还可以通过其他驱动进行自由配置；缺点就是成色好的太贵；

    > Magic Trackpad如今已有两代产品（三代并未有官方的确认）：
    >
    > + 一代年代比较久远，但优点是使用干电池供电（避免使用USB），二手价格适中；缺点是二手存量品质参差不齐，多数面板已经破裂（一般不影响使用），贴膜的办法会影响手感
    > + 二代相比一代面积更大，手感更佳，支持蓝牙和有线；由于内置电池，角度更为平缓，同时也需要连接线进行充电；价格较贵，而且二手品同样也有玻璃面板破裂的问题（较少）

  + **Lenovo K5923**：

    联想十几年前推出的产品，据说销量惨淡，[主要还是windows生态下用户觉得触控板不如鼠标](https://www.zhihu.com/question/290800128)，又或者没有像苹果那样好用的手势操作；现在二手市场上有一些存量，价格很便宜，但90%都丢失了USB接收器，需要自己配，实际效果不得而知；

  + **Logi T651**：

    罗技推出的外接触控板，被誉为Magic Trackpad的最佳替代品；使用Logitech Options在Mac上几乎可以实现Magic Trackpad的所有手势，而且价格相对便宜，唯一的缺点可能也就是在手感上不如Apple；

  + **其他**：

    一般是一些国外的小品牌或者自制的工控触控板，要么不好买要么就是怕踩坑。

+ 综合考量了一下，我还是决定捡一个一代的Magic Trackpad，相信一次Apple的品质。

## Linux下的MagicTrackpad驱动

+ Linux内核[已经适配](https://lkml.iu.edu/hypermail/linux/kernel/1809.2/05203.html)了Magic Trackpad，目前在图形界面上主要有两种驱动：

  + **xf86-input-mtrack**：

    运行在`Xorg`下的一个多触控驱动，提供了非常丰富的设置属性和手势定义，也可以配合`libinput-gestures`来实现更多的手势操作；但是实际在使用Magic Trackpad时问题较多，包括灵敏度过大、手势丢失的问题；而且项目上一个[release](https://github.com/p2rkw/xf86-input-mtrack/releases/tag/v0.5.0)已经是5年前的了，可以说还有很多问题需要解决；
  + **libinput**：

    [freedesktop](https://wayland.freedesktop.org/libinput/doc/latest/what-is-libinput.html)维护的一个外设驱动组件，是现今发行版使用较为普遍的一个外设驱动，兼顾Xorg和Wayland；运行很稳定，我之前使用thinkpad自带的触控板就是默认由`libinput`配置的，同样也支持Magic Trackpad；

+ 使用`libinput`驱动触控板很容易，使用其自带的配置文件已可以达到很好的使用效果。

+ 关于配置文件，默认为`/usr/share/X11/xorg.conf.d/40-libinput.conf`，也可以自行定义，放置在`/etc/X11/xorg.conf.d/`下。

  ```
  Section "InputClass"
          Identifier "libinput touchpad catchall"
          MatchIsTouchpad "on"
          MatchDevicePath "/dev/input/event*"
          Driver "libinput"
          Option "Tapping"      "on"
  		Option "DisableWhileTyping"	"on"
  EndSection
  ```

  > 注意：Linux上使用Magic Trackpad目前存在一个问题（与图形驱动无关），蓝牙连接会不定时断开然后重连，该问题之前已有人在[bluez](https://github.com/bluez/bluez/issues/524)、[kernel](https://bugzilla.kernel.org/show_bug.cgi?id=204589)、[libinput](https://gitlab.freedesktop.org/libinput/libinput/-/issues/898)的bz上进行反馈，基本上所有人都将问题定位在kernel上，但目前尚未得到有效的解决方法。

## MagicTrackpad与libinput-gestures

+ `libinput`只能对触控板实现简单的手势操作（如轻触点击、点击拖动、多指按键定义等），如果想要更加丰富的自定义手势，可以使用`libinput-gestures`来实现。

> 关于`libinput-gestures`对于手势操作的定义和配置，我将会在另外一篇文章中说明。

> 本节所提到的所有操作，均在`Arch Linux`+`Xorg`环境下，如果使用其他发行版或图形环境，可能在某些细节上有所差异。

### libinput-gestures服务的启动

+ `libinput-gestures`的启动方式有两种，`systemd service`方式和`desktop application`方式，通过`libinput-gestures-setup`命令来指定启动方式或者是否自启动。

+ 我们使用`systemd`方式作为user服务来启动：`libinput-gestures-setup service`

+ 这里可能会出现“Systemd not available, can not run as service.”的错误提示，这是因为`libinput-gestures.service`中的`[Install]`是`graphical-session.target`，而我们在user环境下使用的是`default.target`，`libinput-gestures-setup`脚本无法检测到对应的`target`，所以设置失败。

+ 我的解决方法是：

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

+ 设置为`service`方式之后，设置为自动启动：`libinput-gestures-setup autostart`

+ 立即开启`libinput-gestures-setup start`

### libinput-gestures对于设备的选择

> *这里做个记录：*
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

+ libinput-gesture.conf中有关于监听device的相关配置：

  ```bash
  ###############################################################################
  # This application normally determines your touchpad device
  # automatically. Some users may have multiple touchpads but by default
  # we use only the first one found. However, you can choose to specify
  # the explicit device name to use. Run "libinput list-devices" to work
  # out the name of your device (from the "Device:" field). Then add a
  # device line specifying that name, e.g:
  #
  # device DLL0665:01 06CB:76AD Touchpad
  #
  # If the device name starts with a '/' then it is instead considered as
  # the explicit device path although since device paths can change
  # through reboots this is best to be a symlink. E.g. instead of specifying
  # /dev/input/event12, you should use the corresponding full path link
  # under /dev/input/by-path/ or /dev/input/by-id/.
  #
  # You can choose to use ALL touchpad devices by setting the device name
  # to "all". E.g. Do this if you have multiple touchpads which you want
  # to use in parallel. This reduces performance slightly so only set this
  # if you have to.
  #
  # device all
  ```

+ 可以通过`libinput list-devices`来确定使用设备的名称，或者直接设置成all，将会监听所有的设备。

+ 对于我的情况，笔记本内置的和外接的触控板可能都需要使用，所以简单设置为all，避免切换的麻烦。

## USB键盘+MagicTrackpad实现DWT

+ DWT，即“Disable-While-Typing”，是防止在键盘输入时误触触控板的设置。
+ 由于我使用外接USB键盘，并且Magic Trackpad正好放在键盘下方，所以在使用键盘时很容易出现误触的情况。
+ 可以通过在`xorg.conf.d`下的配置文件中添加`Option "DisableWhileTyping"	"on"`来为触控板开启DWT属性。
+ 但仅此我们的外接设备还没有实现DWT的效果，所以我们来看看DWT是如何实现的。

### libinput实现DWT的前提

+ 根据[这篇文章](https://linuxtouchpad.org/libinput/2022/05/07/disable-while-typing.html)所阐述，libinput对于DWT的实现有两种前提条件，满足其中一个即可：

  1. 匹配的键盘和触控板都需要有“internal”的标签（比如不是外接的设备）
  2. 匹配的键盘和触控板的ID是相同的（比如它们的vendor ID和product ID是相同的）

  > 这里要注意，条件1中所述的标签为“internal”的键盘设备不能超过3个，否则不能进行匹配

  ```c
  // libinput关于dwt判断的函数
  static bool 
  tp_want_dwt(struct evdev_device *touchpad,
  	    struct evdev_device *keyboard)
  {
  	unsigned int vendor_tp = evdev_device_get_id_vendor(touchpad);
  	unsigned int vendor_kbd = evdev_device_get_id_vendor(keyboard);
  	unsigned int product_tp = evdev_device_get_id_product(touchpad);
  	unsigned int product_kbd = evdev_device_get_id_product(keyboard);
  
  	/* External touchpads with the same vid/pid as the keyboard are
  	   considered a happy couple */
  	if (touchpad->tags & EVDEV_TAG_EXTERNAL_TOUCHPAD)
  		return vendor_tp == vendor_kbd && product_tp == product_kbd;
  
  	if (keyboard->tags & EVDEV_TAG_INTERNAL_KEYBOARD)
  		return true;
  
  	/* keyboard is not tagged as internal keyboard and it's not part of
  	 * a combo */
  	return false;
  }
  ```

  

+ 实际上，对于笔记本内置的键盘与触控板，已经满足了条件1或2，所以我们在为触控板设置“DWT”属性时，可以顺利地生效。

+ 那么对于外接的键盘与触控板，我们有没有什么办法也让他们成功匹配呢？

+ 当然有办法，就是将他们也设置成“internal”。

+ 所以首先我们要知道这两个属性的来历。

### udev与libinput

+ 一个外接设备从接入到使用的大体流程是这样的（以Xorg为例）：
  + 首先由udev来进行识别与命名，调用不同的rule规则
  + 某些rule规则中会通过读取hwdb来为设备添加一些属性，比如我们上面提到的触控板的“internal”
  + 由xf86-input-libinput通过libinput对设备进行属性配置，比如我们上面提到的键盘的“internal”
+ 关于udev的配置过程，可以通过`udevadm test <dev_path>`了解
  + 使用`libinput list-devices`可以知道某个设备的路径

### keyboard设置internal属性

+ 根据[这篇文章](https://linuxtouchpad.org/libinput/2022/05/07/disable-while-typing.html)所阐述，键盘的“internal”标签是由libinput的[quirks](https://wayland.freedesktop.org/libinput/doc/latest/device-quirks.html)文件来定义的，并且文章中也阐述了如何用自定义的`quirks`文件来覆盖默认的设置。

+ 简单来说，`libinput`的默认`quirks`文件在`/usr/share/libinput/`目录下，一般不建议直接修改，而是创建`/etc/libinput/local-overrides.quirks`（名字是固定的）文件来对默认配置进行覆盖。

+ 比如，在`10-generic-keyboard.quirks`中对键盘做了如下定义

  ```ini
  [Serial Keyboards]
  MatchUdevType=keyboard
  MatchBus=ps2
  AttrKeyboardIntegration=internal
  
  [Bluetooth Keyboards]
  MatchUdevType=keyboard
  MatchBus=bluetooth
  AttrKeyboardIntegration=external
  ```

+ 这里面只有ps2与蓝牙两种，而我的NIZ Atom66键盘使用USB连接，并不匹配这两种类型，因此也就没有`AttrKeyboardIntegration`这个属性。

+ 因此我在`local-overrides.quirks`中直接对设备名字进行匹配，同时添加`AttrKeyboardIntegration=internal`。

  ```ini
  [USB Keyboards]
  MatchUdevType=keyboard
  MatchName=Milsky 66EC-S
  AttrKeyboardIntegration=internal
  ```

+ 之后使用`libinput quirks list <dev_path>`来检验

  ```bash
  $ sudo libinput quirks list /dev/input/event13
  AttrKeyboardIntegration=internal
  ```

### touchpad设置internal属性

> freedesktop的官方文档中，对于[DWT](https://wayland.freedesktop.org/libinput/doc/latest/palm-detection.html#disable-while-typing)的阐述只提及了keyboard的前提，也就是我们上面所说的“internal”属性，并未提及touchpad的前提。
>
> 因为其已默认用户全部都会使用“internal”的，也就是内置的触控板。
>
> 甚至在[external-touchpads](https://wayland.freedesktop.org/libinput/doc/latest/touchpads.html#external-touchpads)章节中，直接表明外接触控板基本不会涉及“拇指触碰”或“手掌触碰”等问题。
>
> 因此`libinput`并没有维护这个属性，而是由`hwdb`配置的。（个人猜测）

+ 根据[这篇文章](http://who-t.blogspot.com/2017/02/libinput-knows-about-internal-and.html)中提到的，触控板的“internal”标签，来自于`hwdb`中定义的`ID_INPUT_TOUCHPAD_INTEGRATION`这个属性，正如前面我们提到，`udev`会查找`hwdb`来为设备配置一些属性；

  > `hwdb`是一个key-value风格的文本数据库，主要用于为`udev`匹配到的硬件设备添加关联属性，也可以用于直接查询。

+ 默认的`hwdb`文件存放在`/usr/lib/udev/hwdb.d/`目录下，同样不建议直接修改，而是创建`/etc/udev/hwdb.d/XX-<filename>.hwdb`文件来对默认属性进行覆盖。

+ 比如，在默认的`70-touchpad.hwdb`文件中，对触控板的`ID_INPUT_TOUCHPAD_INTEGRATION`属性做了如下定义：

  ```
  touchpad:i8042:*
  touchpad:rmi:*
  touchpad:usb:*
   ID_INPUT_TOUCHPAD_INTEGRATION=internal
  
  touchpad:bluetooth:*
   ID_INPUT_TOUCHPAD_INTEGRATION=external
  
  ###########################################################
  # Apple
  ###########################################################
  # Magic Trackpad (1 and 2)
  touchpad:usb:v05acp030e:*
  touchpad:usb:v05acp0265:*
   ID_INPUT_TOUCHPAD_INTEGRATION=external
  ```

+ 可以看到，i8042与usb类型的触控板，都被设置成了“internal”，这也就是为什么内置的触控板可以直接设置DWT的原因。

+ 而对于Magic Trackpad，一代与二代都被设置成了“external”，那么我们也就可以通过在自定义`hwdb`中，将其修改为“internal”来达到目的。

+ 添加的`80-touchpad.hwdb`（注意文件的序号）如下：

  ```
  # Magic Trackpad (1 and 2)
  touchpad:usb:v05acp030e:*
  touchpad:usb:v05acp0265:*
   ID_INPUT_TOUCHPAD_INTEGRATION=internal
  ```

> 修改完配置后，建议重启生效

+ 修改之前，我们可以通过`udevadm info -q property -n <dev_path>`来得知触控板属性

  ```bash
  $ udevadm info -q property -n /dev/input/event6 
  ...
  ID_INPUT_TOUCHPAD_INTEGRATION=external
  ...
  ```

+ 修改之后，我们再查看，**发现这个属性并没有改变**，这是为什么呢？

+ 原来，在`70-touchpad.hwdb`中，Magic Trackpad 1所对应的“v05acp030e”设备匹配条件是usb连接，而实际上我们的触控板是通过蓝牙连接的，这个可以在`udev`配置过程中看到

  ```bash
  $ udevadm test /dev/input/event6 
  ...
  event6: /usr/lib/udev/rules.d/70-touchpad.rules:11 Importing properties from results of builtin command 'hwdb 'touchpad:bluetooth:v05acp030e:name:豆花加辣的 Trackpad:''
  ...
  ```

+ 所以，我们把`80-touchpad.hwdb`下的设备匹配修改一下

  ```
  # Magic Trackpad (1 and 2)
  touchpad:bluetooth:v05acp030e:*
  touchpad:usb:v05acp0265:*
   ID_INPUT_TOUCHPAD_INTEGRATION=internal
  ```

+ 这样就可以匹配到我们的设备了。

+ 最后，来试试外接键盘和触控板的配合，键盘输入时已无法滑动触控板了，完美解决。

## 总结

+ 最后，感谢[who-t](http://who-t.blogspot.com/2017/02/libinput-knows-about-internal-and.html)博客的作者（也是libinput的维护者之一），能够理解我们这些有着“creative arrangement of input devices”的用户

```
yes, I'm sure there's at least one person out there that uses the touchpad upside down in front of the keyboard and is now angry that libinput doesn't allow arbitrary rotation of the device combined with configurable dwt. I think of you every night I cry myself to sleep. 
```

+ 该作者的[另一篇文章](http://who-t.blogspot.com/2016/08/libinput-and-disable-while-typing.html)，对DWT的阐述更佳详细。
