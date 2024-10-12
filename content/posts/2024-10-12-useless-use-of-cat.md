---
title: 用cat命令，是浪费的吗
date: 2024-10-12T00:00:00+08:00
lastmod: 2024-10-12T00:00:00+08:00
draft: false
toc: true
tags:
  - Linux
categories:
  - 饭碗
hiddenFromHomePage: false
hiddenFromSearch: false
---
前不久突然想到一个关于shell的问题：
使用`cat file | grep keyword`，和`grep keyword file`到底有什么不同，孰优孰劣？

之后在StackExchange上的一个[问答](https://superuser.com/questions/192052/advantages-of-cating-file-and-piping-to-grep)里看到了“[UUOC](https://en.wikipedia.org/wiki/Cat_(Unix)#Useless_use_of_cat)”这个概念。

> The purpose of cat is to concatenate (or "catenate") files. If it's only one file, concatenating it with nothing at all is a waste of time, and costs you a process.

大体意思就是以`cat`命令本身设计初衷（连接文件内容），只拿来做一个文件内容的输出，不仅浪费[资源](https://superuser.com/a/192058)，也浪费[时间和一个进程](http://www.smallo.ruhr.de/award.html)。应该使用替代方法就是使用输入重定向`<`，比如把文件内容给一个变量：`a=$(<filename)`；或者配合文本处理的其他命令：`<filename grep keyword`等等。

其实“UUOC”这个说法年代也比较久远了，相关的讨论基本上都是十年之前的了，对于软件和硬件的发展来说，这种影响可能会越来越小，对于大多数人的共识是，使用`cat`来编写，有很高的可读性，代码也更加工整。

但是对于脚本应用场景来说，过于复杂的程序或者性能较差的环境也是[一个重要的考量因素](https://superuser.com/a/323066)，最终的目的是如何更高效地运行，要在多种因素之间做取舍。

这里有一篇[性能测试的比对](http://oletange.blogspot.com/2013/10/useless-use-of-cat.html)，年代久远了但也可以做一个参考。
