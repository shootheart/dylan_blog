---
title: "k8s集群 手动部署"
date: 2022-07-28T00:00:00+08:00
draft: false
toc: true
tags: ["kubernetes"]
categories: ["饭碗"]
---

## 环境

+ vmware虚拟机3台
+ centos7.9 minimal
+ docker 20.10.9
+ k8s 1.24.3

| 主机名     | 规格      | IP             |
| ---------- | --------- | -------------- |
| k8s-master | 2c-2g-40g | 192.168.36.100 |
| k8s-node01 | 2c-2g-40g | 192.168.36.101 |
| k8s-node02 | 2c-2g-40g | 192.168.36.102 |

## 步骤

### 常规配置

```bash
# hosts
192.168.36.100	k8s-master
192.168.36.101	k8s-node01
192.168.36.102	k8s-node02

# 验证网卡mac地址和uuid唯一
cat /sys/class/net/ens160/address
cat /sys/class/dmi/id/product_uuid

# 禁用swap
swapoff -a
# 注释fstab里的swap
sed -i.bak '/swap/s/^/#/' /etc/fstab

# 关闭selinux
setenforce 0
```

{{< admonition quote >}}

至于为什么要关闭swap，借用某博客的一句话“Swap，性能之鸿沟，生死之地，存亡之道，不可不省也。”

{{< /admonition >}}

### 内核配置

```bash
# 永久加载br_netfilter模块
## 在/etc/modules-load.d下添加br_netfilter.conf文件，内容如下：
br_netfilter
## systemd-modules-load服务会在开机时自动探测并加载

# 永久修改内核参数
cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF

sysctl -p /etc/sysctl.d/k8s.conf
```

### 添加k8s软件源

```bash
# repo文件
[kube]
name=kube
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64/
gpgcheck=1
enabled=1
#repo_gpgcheck=1
gpgkey=https://mirrors.aliyun.com/kubernetes/yum/doc/yum-key.gpg https://mirrors.aliyun.com/kubernetes/yum/doc/rpm-package-key.gpg

```

{{< admonition >}}

原文档在repo中添加repo_gpgcheck=1，实测无法验证key，遂将该配置去掉

https://github.com/kubernetes/kubernetes/issues/60134

{{< /admonition >}}

### 配置免密登录

```bash
# master->node01/02 
ssh-keygen -t rsa
ssh-copy-id -i .ssh/id_rsa.pub root@k8s-node01
```

{{< admonition question >}}

原文档是三master节点，配置01->02/03，并未配置master->node，所以需要确认配置的目的

{{< /admonition >}}

### 安装ipvs

```bash
# 安装依赖包
yum install -y conntrack ntpdate ntp ipvsadm ipset jq iptables curl sysstat libseccomp wget vim net-tools git

# 开启ipvs 转发
modprobe br_netfilter
modprobe ip_vs 
modprobe ip_vs_rr 
modprobe ip_vs_wrr 
modprobe ip_vs_sh 
modprobe nf_conntrack

cat > /etc/sysconfig/modules/ipvs.modules << EOF 

#!/bin/bash 
modprobe -- ip_vs 
modprobe -- ip_vs_rr 
modprobe -- ip_vs_wrr 
modprobe -- ip_vs_sh 
modprobe -- nf_conntrack
EOF 
```

### 安装docker

```bash
# 依赖包
yum install -y yum-utils device-mapper-persistent-data lvm2
```

{{< admonition quote >}}

**Device Mapper** 是 Linux2.6 内核中支持逻辑卷管理的通用设备映射机制，它为实现用于存储资源管理的块设备驱动提供了一个高度模块化的内核架构。

{{< /admonition >}}

```bash
# 添加docker源
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 查看可用的docker版本
yum list docker-ce --showduplicates | sort -r

# 安装
yum install docker-ce-20.10.9 docker-ce-cli-20.10.9 containerd.io -y

# 启动docker服务
systemctl start docker
systemctl enable docker
```

{{< admonition info >}}

这里选择可选的最新版20.10.9

{{< /admonition >}}

{{< admonition quote >}}

Docker CE指的是docker社区版，用于为了开发人员或小团队创建基于容器的应用，与团队成员分享和自动化的开发管道。Docker CE版本提供了简单的安装和快速的安装，以便可以立即开始开发。

{{< /admonition >}}

### 安装命令补全

```bash
# 安装bash-completion
yum -y install bash-completion

# 加载bash-completion
source /etc/profile.d/bash_completion.sh
```

{{< admonition quote >}}

Bash自带命令补全功能，但一般我们会安装bash-completion包来得到更好的补全效果，这个包提供了一些现成的命令补全脚本，一些基础的函数方便编写补全脚本，还有一个基本的配置脚本。

{{< /admonition >}}

### 镜像加速

{{< admonition info >}}

主要的加速器有：Docker官方提供的中国registry mirror、阿里云加速器、DaoCloud 加速器，以阿里为例。

{{< /admonition >}}

+ 登陆阿里云容器模块：[https://cr.console.aliyun.com](https://cr.console.aliyun.com/)

+ 按如下配置

  ![image-20220726142855141](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220726142855141.png)

### 验证docker

```bash
docker --version
docker run hello-world
```

+ 以下为正常输出

  ![image-20220726143401637](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220726143401637.png)

### 修改cgroup driver

```bash
# 修改daemon.json，新增exec-opts
{
  "registry-mirrors": ["https://v16stybc.mirror.aliyuncs.com"],
  "exec-opts": ["native.cgroupdriver=systemd"]
}
```

{{< admonition warning >}}

注意json每项后面的“,”

{{< /admonition >}}

{{< admonition >}}

修改cgroupdriver是为了消除告警：
[WARNING IsDockerSystemdCheck]: detected “cgroupfs” as the Docker cgroup driver. The recommended driver is “systemd”. Please follow the guide at https://kubernetes.io/docs/setup/cri/

{{< /admonition >}}

### k8s安装

```bash
# 查看可用的版本
yum list kubelet --showduplicates | sort -r

# 安装
yum install -y kubelet-1.24.3 kubeadm-1.24.3 kubectl-1.24.3

# 修改kubectl使用的cgroupdriver
vi /etc/sysconfig/kubelet
KUBELET_EXTRA_ARGS="--cgroup-driver=systemd"

# 设置kubelet为开机自启动即可，由于没有生成配置文件，集群初始化后自动启动
systemctl enable kubelet
```

{{< admonition info >}}

这里同样使用可用的最新版1.24.3

{{< /admonition >}}

{{< admonition quote >}}

+ **kubelet** 运行在集群所有节点上，用于启动Pod和容器等对象的工具

+ **kubeadm** 用于初始化集群，启动集群的命令工具

+ **kubectl** 用于和集群通信的命令行，通过kubectl可以部署和管理应用，查看各种资源，创建、删除和更新各种组件

{{< /admonition >}}

### kubectl命令补全

```bash
# kubelet命令补全
echo "source <(kubectl completion bash)" >> ~/.bash_profile
source .bash_profile
```

{{< admonition info >}}

kubectl completion命令生成特定shell的补全脚本，可选bash、zsh、fish

{{< /admonition >}}

### 初始化master

```bash
# 初始化master
kubeadm init --kubernetes-version=v1.24.3 --pod-network-cidr=10.224.0.0/16 --apiserver-advertise-address=192.168.36.100 --image-repository registry.aliyuncs.com/google_containers

# 加载环境变量
echo "export KUBECONFIG=/etc/kubernetes/admin.conf" >> ~/.bash_profile
source ~/.bash_profile
```

#### 初始化错误

+ kubeadm初始化错误，提示kubelet服务可能运行不正常，检查kubelet服务状态

  ![image-20220726181319503](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220726181319503.png)

+ kubelet运行错误，可能是因为k8s 1.24已删除dockershim，无法调用docker的原因，需要使用cri-dockerd

  ![image-20220726180416316](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220726180416316.png)

{{< admonition info >}}

使用cri-dockerd：https://blog.csdn.net/wuxingge/article/details/125458691

所有节点都需要安装

{{< /admonition >}}

+ 装完cri-dockerd，重新初始化kubeadm

```bash
# 重置kubeadm
kubeadm reset -f

# 初始化kubeadm，添加cri-socket
kubeadm init --kubernetes-version=v1.24.3 --pod-network-cidr=10.224.0.0/16 --apiserver-advertise-address=192.168.36.100 --image-repository registry.aliyuncs.com/google_containers --cri-socket=unix:///var/run/cri-dockerd.sock
```

### 安装flannel网络

```bash
# 安装
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/2140ac876ef134e0ed5af15c65e414cf26827915/Documentation/kube-flannel.yml
```

#### flannel pod出现问题

![image-20220727140904367](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727140904367.png)

+ 查看kube-flannel-ds-amd64日志

  ![image-20220727141023086](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727141023086.png)

+ 这里提示该pod所使用的serviceaccount用户没有调用api group的权限

  {{< admonition quote >}}

  有关serviceaccount的参考：

  https://www.cnblogs.com/wlbl/p/10694364.html#serviceaccount

  {{< /admonition >}}

+ 这里使用的授权插件是rbac，意思是通过角色控制权限。serviceaccount对象代表一个账号，如果要赋予这个帐号权限，我们还需要一个role对象和一个role与serviceaccount绑定的rolebinding对象，这些都是RBAC插件提供的资源对象。

+ 观察到kube-flannel中有对这些对象的定义，看下执行时提示的问题：

![image-20220727140721180](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727140721180.png)

+ 这里提到ClusterRole和ClusterRoleBinding在v1beta1中找不到定义，所以这些配置没有生效

+ 在yaml里找出这些配置的源码：

  ![image-20220727141830969](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727141830969.png)

  ![image-20220727141844544](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727141844544.png)

+ 使用的api版本都是v1beta1，但是在v1.22+里已经不可用，需要更换成v1

  {{< admonition warning >}}

  参考： https://github.com/kelseyhightower/kubernetes-the-hard-way/issues/612

  *但是我这里安装flannel没有出现warning的提示*

  {{< /admonition >}}

+ 更换之后重新执行，再重启kube-flannel就可以了

  ![image-20220727142349308](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727142349308.png)

### 将work节点加入集群

+ 在master初始化结束时，会返回join所使用的token、discovery-token-ca-cert-hash等信息，如果没有记下来，需要通过以下方式获取：

  ```bash
  # 在master节点执行
  ## 获取token
  kubeadm token list
  
  ## 获取discovery-token-ca-cert-hash
  openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | openssl rsa -pubin -outform der 2> /dev/null | openssl dgst -sha256 -hex | sed 's/^.* //'
  ```

  {{< admonition >}}
  
  token 过期时间是24小时

  certificate-key 过期时间是2小时
  
  {{< /admonition >}}
  
  ```bash
  # 重新生成基础的join命令
  kubeadm token create --print-join-command
  # 添加work节点用生成的命令即可，如果是添加master节点还需要生成certificate-key
  kubeadm init phase upload-certs --experimental-upload-certs 
  # 添加master节点，使用生成的join命令和certificate-key拼接起来即可
  ```
  
  ```bash
  # 在node01和node02上执行，注意和kubeadm init一样要指定cri-socket
  kubeadm join 192.168.36.100:6443 --token 89y41v.eotdhbpk2v0a1n7d --discovery-token-ca-cert-hash sha256:7ad6aecb98f99621297f27e883e3a51d3114cdec64cefeb5d087a96f0fda8804 --cri-socket=unix:///var/run/cri-dockerd.sock
  ```

![image-20220727145534808](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727145534808.png)

![image-20220727150542636](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727150542636.png)

### 安装dashboard

```bash
# 下载yaml
https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-beta8/aio/deploy/recommended.yaml

# 修改镜像地址
sed -i 's/kubernetesui/registry.aliyuncs.com\/google_containers/g' recommended.yaml

# 添加nodeport，外部通过https://NodeIp:NodePort 访问Dashboard
sed -i '/targetPort: 8443/a\ \ \ \ \ \ nodePort: 30001\n\ \ type: NodePort' recommended.yaml

# 增加管理员帐号
cat >> recommended.yaml << EOF
---
# ------------------- dashboard-admin ------------------- #
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dashboard-admin
  namespace: kubernetes-dashboard

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: dashboard-admin
subjects:
- kind: ServiceAccount
  name: dashboard-admin
  namespace: kubernetes-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin

# 安装
kubectl apply -f recommended.yaml
```

#### pod运行失败

+ 查看pod运行状态

  ![image-20220727152736660](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727152736660.png)

+ 查看pod日志

  ![image-20220727152900689](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727152900689.png)

{{< admonition warning >}}

当有多个节点时，安装到非主节点时，会出现一些问题。dashboard使用https去连接apiServer，由于证书问题会导致dial tcp 10.96.0.1:443: i/o timeout。

{{< /admonition >}}

+ 修改recommanded.yaml

```yaml
kind: Deployment
......
    spec:
      nodeName: k8s-master  # 指定安装的节点
      containers:
        - name: kubernetes-dashboard
          image: registry.aliyuncs.com/google_containers/dashboard:v2.0.0-beta8
          imagePullPolicy: Always
          ports:
            - containerPort: 8443
              protocol: TCP
# 每个Deployment下都修改
```

```bash
# 重新安装dashboard
kubectl delete -f recommended.yaml
kubectl apply -f recommended.yaml
```

#### web访问问题

+ 由于设置了NodePort，可以将端口暴露在节点IP上，就可以使用https://<nodeip>:<nodeport>来访问了

+ web访问显示

  ![img](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L0xvdmV5b3Vyc2VsZkppdWhhbw==,size_16,color_FFFFFF,t_70.png)

+ 查看日志，发现是证书问题

  ![image-20220727172308671](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727172308671.png)

+ 最好的解决方法是使用自签证书

```bash
# 由于/etc/kubernetes/pki下已经有ca证书，所以不需要再生成了
# 使用ca证书签发dashboard证书
openssl genrsa -out dashboard.key 2048
openssl req -new -key dashboard.key -out dashboard.csr -subj "/O=white/CN=dashboard"
openssl x509 -req -in dashboard.csr -CA ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -out dashboard.crt -days 3650

# 重新部署kubernetes-dashboard
kubectl delete -f recommended.yaml
kubectl create -f recommended.yaml

# 重新生成secret，指定证书
kubectl create secret generic kubernetes-dashboard-certs -n kubernetes-dashboard --from-file=dashboard.crt=./dashboard.crt --from-file=dashboard.key=./dashboard.key
# 提示kubernetes-dashboard-certs已存在的话，先把已有的secret删掉
kubectl delete secrets kubernetes-dashboard-certs -n kubernetes-dashboard

# 重启kubernetes-dashboard
kubectl delete pod kubernetes-dashboard-659c547786-hcwkz -n kubernetes-dashboard
```

+ 在主机上安装ca证书，之后访问

![image-20220727173034673](https://dylanblog.oss-cn-beijing.aliyuncs.com/2022-07-28-k8s-deploy-manually/image-20220727173034673.png)

+ 创建dashboard-admin用户的token

  ```bash
  kubectl -n kubernetes-dashboard create token dashboard-admin
  ```

{{< admonition failure >}}

网上绝大部份资料，提到创建serviceaccount并绑定clusterrole之后，会自动生成一个secret给该sa，里面附带token，但实测没有。

有关内容见文章末尾。

{{< /admonition >}}

+ 或者可以手动创建一个secret绑定到dashborad-admin

```yaml
# 创建secret
apiVersion: v1
kind: Secret
metadata:
  name: dashboard-admin-secret
  annotations:
    kubernetes.io/service-account.name: dashboard-admin
  namespace: kubernetes-dashboard
type: kubernetes.io/service-account-token


# 将secret加到dashboard-admin
apiVersion: v1
kind: ServiceAccount
metadata:
  creationTimestamp: "2022-07-27T09:36:47Z"
  name: dashboard-admin
  namespace: kubernetes-dashboard
  resourceVersion: "30148"
  uid: 73fb5e3d-8b91-4d3b-bfb2-788451caf418
secrets:
- name: dashboard-admin-secret
```

{{< admonition tip >}}

可以先将dashboard-admin的配置导出成yaml，然后进行修改

kubectl get sa/dashboard-admin -o yaml -n kubernetes-dashboard > dashboardd-admin.yaml

{{< /admonition >}}

{{< admonition quote >}}

#### v1.24开始默认不自动为sa生成secret

+ 发现按照部署操作生成dashborad-admin这个sa，没有查找到对应的secret，正常来说都会通过tokencontroller来自动为其生成secret。

+ 查找资料发现，从v1.24开始LegacyServiceAccountTokenNoAutoGeneration默认为enable，也就是默认不为任何sa自动生成secret

> The `LegacyServiceAccountTokenNoAutoGeneration` feature gate is beta, and **enabled** by default. When enabled, Secret API objects containing service account tokens are no longer auto-generated for every ServiceAccount. Use the [TokenRequest](https://kubernetes.io/docs/reference/kubernetes-api/authentication-resources/token-request-v1/) API to acquire service account tokens, or if a non-expiring token is required, create a Secret API object for the token controller to populate with a service account token by following this [guide](https://kubernetes.io/docs/concepts/configuration/secret/#service-account-token-secrets).

https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.24.md#urgent-upgrade-notes

{{< /admonition >}}

