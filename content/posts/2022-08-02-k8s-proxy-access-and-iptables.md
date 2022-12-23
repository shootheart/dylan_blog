---

title: "k8s配置服务proxy无法访问以及iptables规则梳理"
date: 2022-08-02T00:00:00+08:00
toc: true
tags: ["kubernets"]
categories: ["饭碗"]
lightgallery: true

---

## 环境

- centos7.9
- k8s 1.24.3

## 问题

-  在k8s集群上部署了nginx服务，通过clusterIP方式配置外部访问，之后在master节点上配置proxy代理访问api server。

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1671101074852-9f21bdc1-2491-4b9e-9ad5-2a0c5a5981d2.png" alt="图片.png](https://cdn.nlark.com/yuque/0/2022/png/12871581/1671101074852-9f21bdc1-2491-4b9e-9ad5-2a0c5a5981d2.png#averageHue=%230a0704&clientId=u91e5e809-db05-4&crop=0&crop=0&crop=1&crop=1&from=paste&height=148&id=u615ba899&name=%E5%9B%BE%E7%89%87.png&originHeight=148&originWidth=1217&originalType=binary&ratio=1&rotation=0&showTitle=false&size=28594&status=done&style=none&taskId=uf7126c93-6e8a-493f-be66-076ae14a691&title=&width=1217)![图片.png" referrerPolicy="no-referrer" />



-  在外部浏览器上通过master节点的proxy尝试访问nginx服务，发现无法连接

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1671101106934-31354631-90f7-4640-add8-2ae273a339d5.png" alt="图片.png" referrerPolicy="no-referrer" />



-  正常来说，两个node节点上都存在nginx pod，可以达到负载均衡的效果，但是无论怎么尝试，两个节点上的pod都无法连通。 
-  这种情况在master上使用curl来访问podip也是一样超时，并且podip也无法ping通。 

## 排查

- 由于k8s的各种网络策略都由iptables来执行，由此尝试疏理一下整个数据包的走向以及过滤规则。

### 数据流向

#### master节点

-  根据iptables的数据流，首先进入master节点的`nat-PREROUTING`链: 
```bash
Chain PREROUTING (policy ACCEPT 4660 packets, 212K bytes)
 pkts bytes target     prot opt in     out     source               destination         
14362  654K KUBE-SERVICES  all  --  any    any     anywhere             anywhere             /* kubernetes service portals */
   81  4880 DOCKER     all  --  any    any     anywhere             anywhere             ADDRTYPE match dst-type LOCAL
```
 

- 注释很明确，有关k8s的service都跳到`KUBE-SERVICES`： 
```bash
Chain KUBE-SERVICES (2 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 KUBE-SVC-PIU4JA5FNNNHNOAJ  tcp  --  any    any     anywhere             10.108.94.160        /* nginx-test/nginx-service cluster IP */ tcp dpt:http
    0     0 KUBE-SVC-NPX46M4PTMTKRN6Y  tcp  --  any    any     anywhere             10.96.0.1            /* default/kubernetes:https cluster IP */ tcp dpt:https
    0     0 KUBE-SVC-TCOU7JCQXEZGVUNU  udp  --  any    any     anywhere             10.96.0.10           /* kube-system/kube-dns:dns cluster IP */ udp dpt:domain
    0     0 KUBE-SVC-ERIFXISQEP7F7OF4  tcp  --  any    any     anywhere             10.96.0.10           /* kube-system/kube-dns:dns-tcp cluster IP */ tcp dpt:domain
    0     0 KUBE-SVC-JD5MR3NA4I4DYORP  tcp  --  any    any     anywhere             10.96.0.10           /* kube-system/kube-dns:metrics cluster IP */ tcp dpt:9153
    0     0 KUBE-SVC-Z6GDYMWE5TV2NNJN  tcp  --  any    any     anywhere             10.97.195.35         /* kubernetes-dashboard/dashboard-metrics-scraper cluster IP */ tcp dpt:irdmi
    0     0 KUBE-SVC-CEZPIJSAUFW5MYPQ  tcp  --  any    any     anywhere             10.111.207.171       /* kubernetes-dashboard/kubernetes-dashboard cluster IP */ tcp dpt:https
    4   240 KUBE-NODEPORTS  all  --  any    any     anywhere             anywhere             /* kubernetes service nodeports; NOTE: this must be the last rule in this chain */ ADDRTYPE match dst-type LOCAL
```
 

-  这里规则很多，我们找到匹配ClusterIP的规则，同时也是注释中标明nginx服务的规则，跳转到`KUBE-SVC-PIU4JA5FNNNHNOAJ`: 
```bash
Chain KUBE-SVC-PIU4JA5FNNNHNOAJ (1 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 KUBE-MARK-MASQ  tcp  --  any    any    !10.224.0.0/16        10.108.94.160        /* nginx-test/nginx-service cluster IP */ tcp dpt:http
    0     0 KUBE-SEP-ISOO2NXNTRU4Q4WM  all  --  any    any     anywhere             anywhere             /* nginx-test/nginx-service -> 10.224.1.14:80 */ statistic mode random probability 0.50000000000
    0     0 KUBE-SEP-EKAXC3AGUDPBQ32C  all  --  any    any     anywhere             anywhere             /* nginx-test/nginx-service -> 10.224.2.16:80 */
```
 

- 这里有三条规则 
   1. 第一条说明，访问不是来自flannelIP的，将会跳转到`KUBE-MARK-MASQ`，在目标链中打上标记后回来： 
```bash
Chain KUBE-MARK-MASQ (19 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 MARK       all  --  *      *       0.0.0.0/0            0.0.0.0/0            MARK or 0x4000
```
 

   2. 第二条和第三条，说明访问跳转到`10.224.1.14`和`10.224.2.16`的概率分别是50%，因为在各自跳转的链中，都做了更改对应目的地址的DNAT： 
```bash
Chain KUBE-SEP-ISOO2NXNTRU4Q4WM (1 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 KUBE-MARK-MASQ  all  --  *      *       10.224.1.14          0.0.0.0/0            /* nginx-test/nginx-service */
    0     0 DNAT       tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            /* nginx-test/nginx-service */ tcp to:10.224.1.14:80
---
Chain KUBE-SEP-EKAXC3AGUDPBQ32C (1 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 KUBE-MARK-MASQ  all  --  *      *       10.224.2.16          0.0.0.0/0            /* nginx-test/nginx-service */
    0     0 DNAT       tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            /* nginx-test/nginx-service */ tcp to:10.224.2.16:80
```
  

- 由于目的地址并不在本机，所以会通过路由转发到`flannel.1`网卡，通过`filter-FORWARD`: 
```bash
Chain FORWARD (policy DROP 1286 packets, 57870 bytes)
 pkts bytes target     prot opt in     out     source               destination         
15727  709K KUBE-FORWARD  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes forwarding rules */
15727  709K KUBE-SERVICES  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes service portals */
15727  709K KUBE-EXTERNAL-SERVICES  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes externally-visible service portals */
15727  709K DOCKER-USER  all  --  *      *       0.0.0.0/0            0.0.0.0/0           
15727  709K DOCKER-ISOLATION-STAGE-1  all  --  *      *       0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  *      docker0  0.0.0.0/0            0.0.0.0/0            ctstate RELATED,ESTABLISHED
    0     0 DOCKER     all  --  *      docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  docker0 !docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  docker0 docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  *      *       10.244.0.0/16        0.0.0.0/0           
    0     0 ACCEPT     all  --  *      *       0.0.0.0/0            10.244.0.0/16
```
 

- 第一条规则即时把所有包就交给`KUBE-FORWARD`处理： 
```bash
Chain KUBE-FORWARD (1 references)
 pkts bytes target     prot opt in     out     source               destination         
    0     0 DROP       all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate INVALID
    0     0 ACCEPT     all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes forwarding rules */ mark match 0x4000/0x4000
    0     0 ACCEPT     all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes forwarding conntrack rule */ ctstate RELATED,ESTABLISHED
```
 

- 由于刚刚在`KUBE-MARK-MASQ`已经打了`0x4000`标记，在这里就会被匹配到并`ACCEPT`，由此直接进入`nat-POSTROUTING`： 
```bash
Chain POSTROUTING (policy ACCEPT 2838 packets, 171K bytes)
 pkts bytes target     prot opt in     out     source               destination         
25000 1506K KUBE-POSTROUTING  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes postrouting rules */
    0     0 MASQUERADE  all  --  *      !docker0  172.17.0.0/16        0.0.0.0/0           
    0     0 RETURN     all  --  *      *       10.244.0.0/16        10.244.0.0/16       
    0     0 MASQUERADE  all  --  *      *       10.244.0.0/16       !224.0.0.0/4         
 7317  439K RETURN     all  --  *      *      !10.244.0.0/16        10.224.0.0/24       
    0     0 MASQUERADE  all  --  *      *      !10.244.0.0/16        10.244.0.0/16
```
 

- 在这里，第一条也是直接全部交给`KUBE-POSTROUTING`: 
```bash
Chain KUBE-POSTROUTING (1 references)
 pkts bytes target     prot opt in     out     source               destination         
 3024  182K RETURN     all  --  *      *       0.0.0.0/0            0.0.0.0/0            mark match ! 0x4000/0x4000
    0     0 MARK       all  --  *      *       0.0.0.0/0            0.0.0.0/0            MARK xor 0x4000
    0     0 MASQUERADE  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes service traffic requiring SNAT */
```
 

- 数据包是因为打过标记才走到这条链的，在第二条规则里，这个标记会因为异或操作而被清除，然后在第三条规则里，通过nat的`MASQUERADE`把源地址改为所发出网卡的IP（也就是`flannel.1`），然后通过发到下一个节点（也就是node02）。自此master上的数据流完毕。

#### node02节点

-  数据包从master节点通过`flannel.1`网卡发送到了node02节点，同样从`flannel.1`网卡进入`nat-PREROUTING` 
   - 此时数据包的源地址是`10.224.0.0`，目的地址是`10.224.2.16`
-  node02和master节点的`iptables`规则**基本上是相同的**。所以在nat表中，不会匹配到任何一条规则，直接走到`filter-FORWARD`。 
```bash
# LOG为自行添加调试使用
Chain FORWARD (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination         
  695 58480 KUBE-FORWARD  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* kubernetes forwarding rules */
  581 47724 LOG        all  --  *      *       0.0.0.0/0            10.224.2.16          LOG flags 0 level 4 prefix "[iptables 3:]"
  632 50784 KUBE-SERVICES  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes service portals */
  575 47364 LOG        all  --  *      *       0.0.0.0/0            10.224.2.16          LOG flags 0 level 4 prefix "[iptables 4:]"
  632 50784 KUBE-EXTERNAL-SERVICES  all  --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate NEW /* kubernetes externally-visible service portals */
  632 50784 DOCKER-USER  all  --  *      *       0.0.0.0/0            0.0.0.0/0           
  632 50784 DOCKER-ISOLATION-STAGE-1  all  --  *      *       0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  *      docker0  0.0.0.0/0            0.0.0.0/0            ctstate RELATED,ESTABLISHED
    0     0 DOCKER     all  --  *      docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  docker0 !docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  docker0 docker0  0.0.0.0/0            0.0.0.0/0           
    0     0 ACCEPT     all  --  *      *       10.244.0.0/16        0.0.0.0/0           
    0     0 ACCEPT     all  --  *      *       0.0.0.0/0            10.244.0.0/16       
  554 46104 LOG        all  --  *      *       0.0.0.0/0            10.224.2.16          LOG flags 0 level 4 prefix "[iptables forward-end]"
```
 

   - 在这里也没有任何一条规则会对数据流作出改变，所以会走到最后执行默认策略：`DROP`。这也是访问该pod无法连接的根本原因。

## 解决

-  已知根本原因在于node节点阻止了访问pod的数据包，那解决方法就有两种： 
   -  修改`filter-FORWARD`的默认策略为`ACCEPT` 
> 考虑到全部放行，可能会有未知的问题，暂且不用

 

   -  在`filter-FORWARD`的末尾添加一条兜底策略，放行网卡为`flannel.1`且目的地址为`10.224.X.X`的数据包：
`iptables -A FORWARD -i flannel.1 -d 10.224.2.0/24 -j ACCEPT` 
-  之后再通过外部浏览器访问：

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1671101154065-d965c705-55ec-4a4d-a290-b6f3d6c926ea.png" alt="图片.png" referrerPolicy="no-referrer" />



### 关于FORWARD DROP

- `filter-FORWARD`链的默认策略被置为`DROP`，实际上是`docker`所做的安全策略

> Docker also sets the policy for the `FORWARD` chain to `DROP`. If your Docker host also acts as a router, this will result in that router not forwarding any traffic anymore. If you want your system to continue functioning as a router, you can add explicit `ACCEPT` rules to the `DOCKER-USER` chain to allow it:
>  
>  
> [https://docs.docker.com/network/iptables/#docker-on-a-router](https://docs.docker.com/network/iptables/#docker-on-a-router)

```
$ iptables -I DOCKER-USER -i src_if -o dst_if -j ACCEPT
```

- 所以按官方文档给出的方法，在`DOCKER-USER`链中加入希望开通的转发规则就可以解决。
- 但是按这种方式配置，在系统重启后，这条规则就会时效，所以还是需要配置启动脚本，在docker服务启动之后加载这条规则。

```bash
# /usr/lib/systemd/system/iptables-user.service
[Unit]
Description=
After=docker.service

[Service]
Type=simple
ExecStart=/usr/sbin/iptables -I DOCKER-USER -i flannel.1 -o cni0 -j ACCEPT
ExecReload=
ExecStop=

[Install]
WantedBy=multi-user.target
```
