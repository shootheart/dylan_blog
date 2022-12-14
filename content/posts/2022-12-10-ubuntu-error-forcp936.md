---

title: "ubuntu挂载cifs无法使用cp936字符集"
date: 2022-12-10T00:00:00+08:00
toc: true
tags: ["gerq"]
categories: ["fer"]

---

## 环境

- ubuntu 20.04.4

## 问题

- 使用multipass启动了ubuntu虚拟机，想要让其与win10宿主机共享目录，由于multipass提供的mount方法在虚拟机重启后就会失效，所以决定还是用smb来挂载。
- 共享目录需要支持中文显示，在添加fstab条目时需要指定iocharset选项

```bash
# /etc/fstab
//172.28.192.1/python /media/share      cifs    defaults,iocharset=cp936,uid=1001,gid=4        0 0
```

- 执行`mount -a`时发生错误，查看syslog发现无法找到cp936字符集

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1670996999107-40b903d0-f9e9-4513-b703-64892e011b62.png" alt="图片.png" referrerPolicy="no-referrer" />



## 解决

-  在askubuntu上找到了类似的问题，原因是缺少模块文件。 
-  查看`/lib/modules/$(uname -r)/kernel/fs/nls/`是否存在对应字符集的模块。 
-  若缺少，需要安装包含该模块的内核包，比如`linux-generic`或`linux-image-extra-virtual` 
-  我的系统中已经安装了`linux-generic`内核，所以只需要安装`linux-image-extra-virtual`重启即可。 

> 参考：[https://askubuntu.com/questions/519796/unable-to-mount-cifs-with-iocharset-utf8](https://askubuntu.com/questions/519796/unable-to-mount-cifs-with-iocharset-utf8)

