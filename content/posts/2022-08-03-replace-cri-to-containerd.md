---

title: "k8s v1.24.3更换容器运行时为containerd"
date: 2022-08-03T00:00:00+08:00
toc: true
tags: ["kubernets"]
categories: ["饭碗"]

---

## 环境

- CentOS 7.9
- k8s 1.24.3
- containerd 1.6.6

## 背景

-  k8s从1.20开始逐步放弃使用docker作为容器运行时环境，1.24开始已经删除dockershim，如果还希望使用docker，就要安装cri-docker来进行调用，无疑是需要多一个调用链。所以不如放弃docker，直接调用containerd。

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1671779618869-3cc054e6-0ecc-4a3b-acff-4344c730084c.png" alt="image.png" referrerPolicy="no-referrer" />



## 步骤

- 首先在master节点上将要更换的节点清空：`kubectl drain k8s-node01 --ignore-daemonsets`
- 在要更换的节点上停止`kubelet`和`docker`服务
- 如果未安装`containerd`的需要安装，已安装的将原有配置文件替换`containerd config default | tee /etc/containerd/config.toml` 
   - 在配置文件中，注意`sandbox_image`项，默认为`"k8s.gcr.io/pause:3.7"`，可以替换成你想要使用的`pause`镜像。
- 重启containerd服务
- 在节点的`kubelet`配置文件里，将`crisocket`更换成`containerd.sock`的文件路径。 
   - 一般在`/var/lib/kubelet/kubeadm-flags.env`中修改`--container-runtime-endpoint`项即可
- 重启kubelet服务
- 在master节点上恢复节点状态：`kubectl uncordon k8s-node01`，并观察节点状态。
- 节点状态恢复正常，即可卸载docker组件：`yum remove docker-ce docker-ce-cli` 
   - **注意不要将containerd连带删除**
