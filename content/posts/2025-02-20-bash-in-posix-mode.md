---
title: 为什么systemd中用sh执行source命令有问题
subtitle: bash的POSIX模式
date: 2025-02-20T00:00:00+08:00
lastmod: 2025-02-20T00:00:00+08:00
draft: false
toc: true
tags:
  - Linux
categories:
  - 饭碗
hiddenFromHomePage: false
hiddenFromSearch: false
---

## 问题

尝试在一个systemd的service里以`sh`执行一个脚本，脚本中包含了一条`source test1.sh`的命令

但是在启动service时，却报出了`source: test1.sh: file not found`的错误（注意是文件不存在，而不是命令），而且在source执行报错后，脚本就退出不执行了。

我已经在service里指定了`WorkingDirectroy`变量，并且test1.sh文件的路径也没有问题，所以排除路径的问题。

而我尝试在shell上同样以`sh`命令执行这个脚本，却发现可以正常执行。

如果我把service里的`sh`改为`bash`，也可以正常执行。

如果我将脚本中的source改成`source ./test1.sh`，也可以正常执行。

所以，能得出以下结论：
1. systemd里`bash`与`sh`的执行有差异
2. `sh`在systemd和本地shell里执行有差异
3. `source`的文件是否带有路径会有差异

## 探究

首先，我将service里的命令修改为`bash`，就可以正常执行，那是否因为是两个shell的原因？

但实际上，现在绝大多数的操作系统，都已经将`/bin/sh`链接到`bash`了，所以他们执行的其实都是`bash`。

先去`man bash`里看看`source`这个命令
```
    If filename does not
    contain a slash, filenames in PATH are used to find the
    directory containing filename, but filename does not need
    to be executable. 
```
如果文件名不带有"/"，那将在`PATH`里寻找文件
```
    When bash is not in posix mode, it searches
    the current directory if no file is found in PATH.
```
在非posix模式下，最后会搜索当前目录查找文件

那问题可能是在这个差异上。

Bash如果以`sh`命令执行，将进入POSIX模式
```
    When invoked as 'sh', Bash enters POSIX mode after reading the startup
files.
```
也就是我在service里指定的，其实是以POSIX模式执行的`bash`。

那如果是posix模式，会如何搜索，看下bash这[两种模式的差异](https://tiswww.case.edu/php/chet/bash/POSIX)
```
    43. The '.' and 'source' builtins do not search the current directory
     for the filename argument if it is not found by searching 'PATH'.
```
在posix模式下，`source`和`.`命令不会搜索当前目录来查找文件，而是只在`PATH`里搜索

那可以得出结论，以POSIX模式执行的`bash`，内置的`source`命令不会在当前目录下搜索一个不带"/"的文件名，它只能去`PATH`里搜索。

那为什么在正常shell中以`sh`执行，不会有问题？

之前参考了在shell和systemd中执行`sh`命令的[区别](https://unix.stackexchange.com/a/339645)，我猜测是因为non-interactive的原因
但是我又仔细看了关于`source`命令的搜索规则，没有发现与是否是交互式shell有关的信息
那就来比较了一下两种情况的shell参数：打印一下`set`
发现了以下区别：
``` bash
# shell下（交互式)
PATH=/opt/jdk1.8.0_151/bin:/opt/jdk1.8.0_151/jre/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin:
# systemd下（非交互式)
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
```

交互式shell的PATH变量在结尾多了一个空值（null），而在bash里对这个值的解释如下：
```
    A zero-length (null) directory
    name in the value of PATH indicates the current directory.
    A null directory name may appear as two adjacent colons, or
    as an initial or trailing colon.
```
这个空值代表当前目录，那这就正好对应了bash在posix模式下`source`命令的搜索规则，也就解释了为什么我在shell下可以正常执行

我看一下systemd里的环境变量：`systemctl show-environment`
```
LANG=zh_CN.UTF-8
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
```
确实是不包含当前目录的，而以`sh`启动`bash`的情况，在非交互模式下应该也不会执行其他的初始化，所以这个`source`命令就无法找到不带路径的文件了。

为什么执行到`source`失败后脚本就退出了？

还是bash这[两种模式的差异](https://tiswww.case.edu/php/chet/bash/POSIX)
```
    24. If a POSIX special builtin returns an error status, a
     non-interactive shell exits.
```

## 如何修改

既然知道了原因，那就有对应的办法：
1. 像之前一样修改成`bash`执行
2. 在脚本里修改`PATH`变量
3. 在脚本里执行一下`systemctl import-environment PATH`同步一下，但是这种方式应该会是全局的
4. 在service里手动指定`PATH`变量，但这种方式必须写全部的，不能引用`$PATH`

