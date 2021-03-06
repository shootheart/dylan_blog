# CA证书与中间人攻击



## 前言

+ 由于偶然在群中有人聊起如何抓包https，从而找了一下有什么方法可以实现。
+ 查到Charles这个工具可以实现https的抓包，而且可以查看其中的的数据内容。主要的原理为中间人代理（就是中间人攻击）。
+ 因为https是加密数据的，所以使用正常抓包方法即时可以抓到数据包，也无法像http一样查看其中的内容。
+ ![img](https://dylanblog.oss-cn-beijing.aliyuncs.com/2018-12-29-CA-certificate-and-middleman-attack/20180521084049872)
+ Charles是拦截https的数据包，并使用自己的证书来伪装成服务器的证书发给客户端来完成认证，那么对此就有一个问题，既然中间人可以这么轻易拦截报文并伪装，怎么还能保证https的安全性呢，认为突破点在于对证书的信任验证。

## 主机对CA证书的信任

+ 当客户端与服务器使用https进行通信的时候，客户端对发来的ca证书肯定是会进行验证的，如果验证不可信，浏览器就会提醒用户该网站不可信。那么想要达到可信的效果，中间人只有两个办法，一个是强制将自己的证书安装在客户端上，第二个就是要伪造成原服务器的证书。
+ 正常的数字证书中还包括ca机构对该证书的签名（使用ca公钥加密），如果有改动，当浏览器对篡改后的信息进行校验就会不通过，所以如果我们使用第二种方法进行伪造，有一个解决办法就是让证书尽量看起来是ca颁发的，我们可以用我们随机生成的密钥对来做自签发的证书，这样在客户端的浏览器上依然会出现证书不信任的字样，但是当用户查看过证书的内容后，极有可能会选择信任该证书。
+ 对于检查证书严格的情况，此方法也不能成功，所以在一定程度上来讲，https还是比较安全的。
+ **猜测中间人使用合法的CA证书是否可以直接信任，后来发现即使最简单申请的DV证书，也是基于域名申请的，此方法当然行不通。**

## 对于访问网站获取CA证书与缓存

+ 在此发现一个问题，操作系统安装或浏览器安装的时候，经常会默认安装一些CA机构的根证书，但是对这些机构颁发的具体网站的证书没有导入系统。
+ 我们测试在新安装系统上访问一个https的网站，发现https是正常的，说明证书校验通过，但是检查系统的ca证书库中并没有导入这个网站的证书，在访问的过程中也没有提示需要导入证书。
+ 对于这个问题，解释是，当系统安装了一个CA机构的根证书，对于该证书链下的所有经过CA颁发的证书都会信任，但是并不会在系统中保存这个证书。服务器在每次https握手阶段都会发送证书，为了加快握手的速度，降低资源消耗，有一种说法是缓存的是TLS的会话信息。

> 来源：腾讯
>
> 为了加快建立握手的速度，减少协议带来的性能降低和资源消耗，TLS协议有两类会话缓存机制：会话标识Session ID与会话记录Session Ticket。
>
> Session ID由服务器端支持，协议中的标准字段，因此基本所有服务器都支持，服务器端保存会话ID以及协商的通信信息，Nginx中1M内存约可以保存4000个Session ID机器相关信息，占用服务器资源较多；
>
> Session Ticket需要服务器和客户端都支持，属于一个扩展字段，支持范围约60%（无可靠统计与来源），将协商的通信信息加密之后发送给客户端保存，密钥只有服务器知道，占用服务器资源很少。
>
> 二者对比，主要是保存协商信息的位置与方式不同，类似于http中的session于cookie。
>
> 二者都存在的情况下，优先使用session_ticket（Nginx实现）。


