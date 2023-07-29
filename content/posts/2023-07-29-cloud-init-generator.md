---
title: "cloud-init-generator"
date: 2023-07-29T00:00:00+08:00
draft: false
toc: true
tags: ["cloud", "云计算", "cloud-init"]
categories: ["饭碗"]
---

## 问题说明

+ `cloud-init 18.5`开始，服务的自启动机制改变了，由`cloud-init-generator`脚本来决定`cloud-init`是否跟随系统启动

+ 整体策略：

  ```bash
  # enable AND ds=found == enable
  # enable AND ds=notfound == disable
  # disable || <any> == disabled
  ```

## 流程梳理

### 1. 确定是否有禁用标识

+ 首先从`cmdline`中找是否存在`cloud-init`参数，并且是否为`enabled`
+ 然后找`/etc/cloud/`目录下是否有`cloud-init.disabled`或`cloud-init.enabled`标识文件
+ 如果上面两个都没有指定，就使用默认`enabled`，即没有禁用。

### 2. 寻找datasource

+ 检查是否存在`/usr/lib/cloud-init/ds-identify`，并且是可执行的，如果不是，就直接结束，没有找到ds。如果是，就执行这个脚本。
  + 新版本的路径改到了`/usr/libexec/cloud-init/ds-identify`

#### ds-identify

+ `ds`的来源：

  + `cmdline`参数：可以指定`ci.ds`、`ci.datasource`、`ci.di.policy`
  + `config`：查找`cloud.cfg`中的`datasource_list`
  + 都没有的话，用默认的列表

+ 如果是使用默认的列表，将会针对每个`datasource`类型进行可用性检查，每一个都定义了对应的方法

  + 以`configdrive`为例，`collect_info`方法中已经通过`read_fs_info`方法找到了`label`为`config-2`的分区/盘，所以`dscheck_ConfigDrive`方法检查确认存在`datasource`

+ `ds`的查找有三种结果：

  ```bash
  #   found,maybe,notfound:
  #      found: (default=all)
  #         first: use the first found do no further checking
  #         all: enable all DS_FOUND
  #
  #      maybe: (default=all)
  #       if nothing returned 'found', then how to handle maybe.
  #       no network sources are allowed to return 'maybe'.
  #         all: enable all DS_MAYBE
  #         none: ignore any DS_MAYBE
  #
  #      notfound: (default=disabled)
  #         disabled: disable cloud-init
  #         enabled: enable cloud-init
  
  ```

+ 如果找到了第一个found的`ds`，就成功

+ 如果没有found的`ds`，就要在maybe里来找

  + 只要有一个maybe的`ds`，并且`policy`里的maybe不等于`none`，也成功

+ 如果都没有，就要进行四种组合的判断（`mode`和`policy`里的notfound）：

  + search:disabled->disabled
  + search:enabled->enabled
  + report:disabled->enabled
  + report:enabled->enabled

+ 四种`mode`的解释：

  ```bash
  #   Mode:
  #     disabled: disable cloud-init
  #     enabled:  enable cloud-init.
  #               ds-identify writes no config and just exits success.
  #               the caller (cloud-init-generator) then enables cloud-init to
  #               run just without any aid from ds-identify.
  #     search:   determine which source or sources should be used
  #               and write the result (datasource_list) to
  #               /run/cloud-init/cloud.cfg
  #     report:   basically 'dry run' for search.  results are still written
  #               to the file, but are namespaced under the top level key
  #               'di_report' Thus cloud-init is not affected, but can still
  #               see the result.
  ```

### 3. 执行generator

+ 根据`ds-identify`返回的结果，确定是否启动cloud-init
+ 如果确定启动，检查`/run/systemd/generator.early/multi-user.target.wants/cloud-init.target`链接是否存在，不存在就创建，同时建立一个`/run/cloud-init/enabled`标识文件（不管链接文件创建成功与否都有）
+ 如果确定禁用，则与上述相反

> 所有`[Install]`被配置为`WantsBy=cloud-init.target`的`service`（也就是`cloud-init`的四个`service`），都必须进行`enable`操作，否则无法启动