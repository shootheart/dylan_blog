---
title: "Let's Encrypt证书申请"
date: 2019-03-01T00:00:00+08:00
draft: false
toc: true
tags: ["https","web"]
categories: ["饭碗"]
---


## 环境

+ CentOS 7
+ Python 2.7.5

## 安装

+ 直接使用yum安装certbot

``` bash
yum install certbot
```

## 申请证书

+ 确保服务器域名与公网IP绑定。
+ 申请过程中需要使用80端口，若占用可以先关闭。
+ **国内DNS可能会获取不到域名信息。**（未测试）

``` bash
# 获取证书（邮箱可选填）
certbot certonly --standalone -d shootheart.rocks --email liuch1207@sina.com
```

+ 出现“Congratulations”字样说明证书获取成功，证书存放在/etc/letsencrypt/live/shootheart.rocks/目录下，共有四个文件：
  + cert.pem  - Apache服务器端证书
  + chain.pem  - Apache根证书和中继证书
  + fullchain.pem  - Nginx所需要ssl_certificate文件
  + privkey.pem - 安全证书KEY文件

## 将证书添加到Web服务器

+ 编辑/etc/httpd/conf.d/ssl.conf

``` bash
# Apache服务器
vi /etc/httpd/conf.d/ssl.conf

# 修改配置
SSLEngine on
SSLCertificateFile /etc/letsencrypt/live/shootheart.rocks/cert.pem
SSLCertificateKeyFile /etc/letsencrypt/live/shootheart.rocks/privkey.pem
```

+ 默认免费证书有效期90天，需要在即将到期时手动续期或自动续期才可以继续使用。

``` bash
# 手动续期，若证书未到期，可以强行续期--force-renew
certbot renew

# 也可以配合crontab自动续期
```

