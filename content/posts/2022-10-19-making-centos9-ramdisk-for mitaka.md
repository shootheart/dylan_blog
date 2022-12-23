---

title: "制作openstack-mitaka版centos9裸机ramdisk"
date: 2022-10-19T00:00:00+08:00
toc: true
tags: ["OpenStack"]
categories: ["饭碗"]

---

## 环境

- openstack：mitaka；ironic：5.1.0
- 制作环境：centos7.9；python：3.6.8
- ironic-python-agent：1.2.3；ironic-lib：1.2.0

> 制作环境建议至少4G内存


## 制作

### 安装工具

```bash
# 安装依赖工具
yum install qemu-img yum-utils bind-chroot git gdisk

# 如果没有安装python和pip，需要单独安装
yum intall python3 python3-pip

# 安装ironic-python-agent-builder和diskimage-builder
pip3 install ironic-python-agent-builder diskimage-builder
```

### 下载需要的文件

```bash
# 下载ironic-python-agent和ironic-lib
curl -O https://tarballs.opendev.org/openstack/ironic-python-agent/ironic-python-agent-1.2.3.tar.gz
curl -O https://tarballs.opendev.org/openstack/ironic-lib/ironic-lib-1.2.0.tar.gz

# 下载依赖软件列表
curl -O https://opendev.org/openstack/requirements/raw/tag/mitaka-eol/upper-constraints.txt
```

### 修改source-repositories

-  因为直接使用ironic-python-agent-builder，会直接从openstack的git仓库上下载ironic-python-agent、ironic-lib和upper-constraints.txt文件，虽然可以指定发行版，但如今已不直接提供mitaka版（但是有对应版本的tag，未验证），所以需要手动指定这三个文件的来源 
-  首先找到ironic-python-agent dib的路径 
```bash
cd /usr/local/share/ironic-python-agent-builder/dib/
```
 

-  上面提到的三个文件的来源，在ironic-python-agent-ramdisk目录中定义，以"source-repository-名称"为文件名 
-  文件格式如下： 
```
<name> <type> <destination> <location> [<ref>]
名称	  类型		目标		文件位置  可选，取决于类型
```
  

-  我们将三个文件的来源指定为我们下载好的本地文件 
```bash
# source-repository-ironic-python-agent
ironic-python-agent tar /tmp/ironic-python-agent file:///root/ironic-python-agent-1.2.3.tar.gz

# source-repository-ironic-lib
ironic-lib tar /tmp/ironic-lib file:///root/ironic-lib-1.1.0.tar.gz

# source-repository-requirements
requirements file /tmp/requirements/upper-constraints.txt file:///root/upper-constraints.txt
```
 

### 制作镜像

-  首先定义环境变量 
```bash
export DIB_DEV_USER_PWDLESS_SUDO="yes"		# 设置sudo可以免密执行
export DIB_DEV_USER_USERNAME="user"			# 定义ramdisk的用户
export DIB_DEV_USER_PASSWORD="password"		# 定义ramdisk的密码
export DIB_DISABLE_KERNEL_CLEANUP=1
```
 

-  执行ironic-python-agent-builder命令 
```bash
ironic-python-agent-builder -o mitaka-centos9 -e dhcp-all-interfaces -e devuser -r 9-stream centos -v | tee build.log
# -o 为输出文件的名称前缀
# -e 为附加的elements
# dhcp-all-interfaces表示启动镜像后扫描所有的网络端口的dhcp
# devuser支持创建用户
# -r 为使用的发行版版本号
# centos为使用的发行版
# -v 输出debug内容
```
    

-  执行完毕，会生成`mitaka-centos9.kernel`、`mitaka-centos9.initramfs`、`mitaka-centos9.d`（不需要） 

## 启动

-  将小镜象上传至openstack 
```bash
glance image-create --name mitaka-centos9-kernel --disk-format aki --container-format aki --file mitaka-centos9.kernel  --progress

glance image-create --name mitaka-centos9-ramdisk --disk-format ari --container-format ari --file mitaka-centos9.initramfs  --progress
```
 

-  然后将小镜象配置到ironic node上 
```bash
ironic node-update <uuid> replace driver_info/deploy_kernel=<kernel_uuid> driver_info/deploy_ramdisk=<ramdisk_uuid>
```
 

-  之后新建裸机的实例测试 
