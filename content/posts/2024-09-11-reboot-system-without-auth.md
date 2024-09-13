---
title: 如何不让我轻易地执行关机重启
date: 2024-09-11T00:00:00+08:00
lastmod: 2024-09-11T00:00:00+08:00
draft: false
toc: true
tags:
  - Linux
  - Arch
categories:
  - 饭碗
hiddenFromHomePage: false
hiddenFromSearch: false
---
## 起因

还得从一次意外关机讲起，用这么多年还真没有注意到这个问题。。

我在终端里ssh远程了一台服务器（虚拟机），本来打算用完之后在终端上将其关机的，于是在我输入了两次`exit`（服务器上正在登录一个从root切换过去的普通用户，而我却没有意识到自己敲了两次exit）之后，直接输入了`systemctl poweroff`，此时的终端是我本机的，然后就直接被关机了。

## 溯源

虽说关机的命令可以在普通用户下直接执行（加入了wheel用户组），却极少情况这么使用过，也就没有意识到这个误输入的问题，既然发现了，就得想办法避免一下，这次是没有什么重要的数据未保存，谁知道下次呢。

`systemd`的有关电源操作，基本上是由`logind`负责的，而命令执行必然要经过`polkit`来鉴权，这就需要了解一下这些操作是怎么定义授权规则的。

查看一下有关`logind`的规则
`/usr/share/polkit-1/action/org.freedesktop.login1.policy`
```xml
        <action id="org.freedesktop.login1.reboot">
                <description gettext-domain="systemd">Reboot the system</description>
                <message gettext-domain="systemd">Authentication is required to reboot the system.</message>
                <defaults>
                        <allow_any>auth_admin_keep</allow_any>
                        <allow_inactive>auth_admin_keep</allow_inactive>
                        <allow_active>yes</allow_active>
                </defaults>
                <annotate key="org.freedesktop.policykit.imply">org.freedesktop.login1.set-wall-message</annotate>
        </action>


        <action id="org.freedesktop.login1.power-off">
                <description gettext-domain="systemd">Power off the system</description>
                <message gettext-domain="systemd">Authentication is required to power off the system.</message>
                <defaults>
                        <allow_any>auth_admin_keep</allow_any>
                        <allow_inactive>auth_admin_keep</allow_inactive>
                        <allow_active>yes</allow_active>
                </defaults>
                <annotate key="org.freedesktop.policykit.imply">org.freedesktop.login1.set-wall-message</annotate>
        </action>
```
`reboot`和`power-off`两个操作的规则是一样的，本地会话的用户可以跳过密码直接授权，这样确实会有问题，而我们的目的不是拒绝操作，起码也要有一个验证来缓冲一下这种危险的行为。

## 尝试

在`/etc/polkit-1/rules.d/`下添加一个优先规则`40-nopower.rules`，参考自[ArchBBS](https://bbs.archlinux.org/viewtopic.php?id=152565)

```javascript
polkit.addRule(function(action, subject) {
	if (action.id.indexOf("org.freedesktop.login1.power-off") == 0 ||
      action.id.indexOf("org.freedesktop.login1.reboot") == 0) {
		return polkit.Result.AUTH_ADMIN;
	}
});
```

`polkit`规则可以动态加载，无需重启服务
可以用`pkcheck`来验证是否生效
`$ pkcheck -u -p $$ -a org.freedesktop.login1.reboot`
但命令返回是0，并且执行也没有任何需要鉴权的提示，说明并没有生效

## 改进

还是ArchBBS，搜到了一篇[更近的帖子](https://bbs.archlinux.org/viewtopic.php?id=251118)，里面提到`systemd`在reboot增加了更多的授权，所以只设定其中一个的规则，是无法达到效果的。于是规则修改成下面这样：

```javascript
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.login1.power-off" ||
        action.id == "org.freedesktop.login1.power-off-ignore-inhibit" ||
        action.id == "org.freedesktop.login1.power-off-multiple-sessions" ||
        action.id == "org.freedesktop.login1.set-reboot-parameter" ||
        action.id == "org.freedesktop.login1.set-reboot-to-firmware-setup" ||
        action.id == "org.freedesktop.login1.set-reboot-to-boot-loader-menu" ||
        action.id == "org.freedesktop.login1.set-reboot-to-boot-loader-entry" ||
        action.id == "org.freedesktop.login1.reboot" ||
        action.id == "org.freedesktop.login1.reboot-ignore-inhibit" ||
        action.id == "org.freedesktop.login1.reboot-multiple-sessions"
    ) {
        return polkit.Result.AUTH_SELF_KEEP;
    }
});
```

再使用`pkcheck`验证，就能明显看到鉴权提示了，说明规则生效。

## 新问题

这样做虽然解决了通过命令行直接关机的问题，但是我使用的`xfce`电源控制键也被屏蔽掉了，社区有人讨论过一个[解决方案](https://bbs.archlinux.org/viewtopic.php?id=251118)，但无论是修改执行权限还是删除依赖，都觉得不是最完美的解决方法。