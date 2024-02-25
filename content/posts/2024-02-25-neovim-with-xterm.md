---
title: 使用xterm打造GUI版neovim
date: 2024-02-25T00:00:00+08:00
lastmod: 2024-02-25T00:00:00+08:00
draft: false
toc: true
tags:
  - Linux
  - Arch
  - vim
categories:
  - 饭碗
hiddenFromHomePage: false
hiddenFromSearch: false
---

## 前言

`neovim`作为`vim`的升级版（更应该叫改进版），越来越赢得用户们的青睐，但是官方并没有一个类似`gvim`的应用，可以脱离终端来使用，即便已经有各类基于各种语言所编写的GUI应用，实际使用下来好像也没有一个可以称得上“轻量级”的，毕竟对于我这种“内存焦虑症”患者，资源少性能高才是终极目标。

## 需求

我使用的系统为Arch Linux+Xfce桌面，终端使用默认的`xfce4-terminal`，在使用`neovim`时，要么是直接在终端里运行，要么是从thunar里点击文件运行，但是无论哪种方式，neovim都是依附于terminal运行的，当我切换应用时，有时就会分不清哪个是终端，哪个是neovim（改终端标题也是一个办法，但plank会将他们全部合并到terminal的应用图标上，依然不好区分）。

所以我的需求很明确：在不使用已有GUI版nvim的情况下，将neovim作为一个单独的GUI应用，并且能够实现从thunar点击文件，不开启新窗口，而是以tab形式打开。

## xterm的配置

由于我使用X11，xterm已经预装到系统里了，既然neovim必须要运行在一个终端里，那何不让它从xterm里启动呢，这样就可以和xfce的终端区分开了。

> 这个想法，已经使用lxce-terminal验证过了，因为它和xterm一样占用资源低。

xterm默认的样式很不友好，需要对其进行配置

编辑`~/.Xresources`文件

```config
!! 配置字体
xterm*renderFont: true
xterm*faceName: DejaVu Sans Mono Book
xterm*faceSize: 13

!! 配置鼠标样式
XTerm*pointerShape: left_ptr
Xcursor.size:	0

!! 配置背景色和前台颜色
xterm*background:	rgb:00/00/00
xterm*foreground:	rgb:a8/a8/a8
```

之后将其应用到xterm：
`xrdb -merge ~/.Xresources`

再打开xterm，看起来就比较舒服了。

> [关于xrdb与Xresources的wiki](https://wiki.archlinux.org/title/X_resources)

## 配置启动器

> 建议在`$HOME/.local/share/applications/`目录下新建.desktop文件，而不是直接修改`/usr/share/applications/`下的文件。
> 也可以将系统目录下的desktop文件copy到用户目录，然后修改。

```desktop
[Desktop Entry]
Name=Nvim
...
TryExec=nvim
Exec=/usr/bin/xterm -T "NVIM" -e "nvim" %F
Terminal=false
Type=Application
...
```

这样，就可以实现从文件管理器中选择文件打开，我们会看到运行在xterm中的neovim。

## 配置追加标签页打开文件

以上配置只能满足我们的基本要求，即在文件管理器（如thunar）中点击文件，neovim可以以一个单独的GUI应用显示。

但很多时候，我们会继续打开其他文件，我们希望新打开的文件不要出现在新窗口中，而是在已有窗口中以标签页形式出现（[vim/neovim中的buffer概念](https://blog.csdn.net/jy692405180/article/details/79775125)，建议neovim安装bufferline插件，以便显示多个buffer）。

这里就要用到neovim的[远程执行功能](https://neovim.io/doc/user/remote.html)，首先需要运行一个server端，之后的实例，以client端形式将文件发送给server端打开。

例如：我们打开的第一个文件，nvim是以server形式运行的，只要它没有关闭，之后打开的nvim就以client运行，将文件在第一个实例上打开，就相当于在其上新打开了一个buffer。

我们可以通过脚本来实现：

```bash
PIPE=/run/user/$UID/nvim.pipe
[ ! -O $PIPE ] &&  exec /usr/bin/xterm -maximized -T "Neovim" -e "/usr/bin/nvim --listen $PIPE $@" || \
	(/usr/bin/xdotool search --classname xterm windowactivate;/usr/bin/nvim --server $PIPE --remote $@)

# vim:ft=sh
```

由于这种方式打开新文件并不会像普通编辑器那样把窗口移动到前台，所以我们用xdotool将窗口激活来实现相同的效果。

最后我们在启动器内修改执行命令：

```desktop
[Desktop Entry]
Name=Nvim
...
TryExec=nvim
Exec=~/.local/bin/nv %F
Terminal=false
Type=Application
...
```

