---

title: "OpenStack部署裸金属无法启动cloud-init"
date: 2023-05-17T00:00:00+08:00
toc: true
tags: ["OpenStack"]
categories: ["饭碗"]

---

+ + 云环境：OpenStack Mitaka
+ 裸机系统：BCLinux 8
+ cloud-init 19

## 问题

+ 通过OpenStack部署裸金属，系统镜像安装完毕后重启，`cloud-init`无法启动（共四个服务都没有启动）。同qcow2镜像在KVM环境里可以正常进行初始化
+ 如果使用`cloud-init` 18.2，可以正常启动（先前用rhel7.8测试通过），但一旦使用18.5以上就会出现上述问题。
+ 使用本地单独KVM环境测试，18.5以上的`cloud-init`同样无法启动。

## 分析

+ `cloud-init` 18.5相比18.2，有如下区别：

  + 18.2中四个服务都在`multi-user.target.wants`中，跟随系统启动；18.5中，四个服务在`cloud-init.target.wants`中，`cloud-init.target`被设置成在`multi-user.target`之后启动

    ```bash
    # 18.5
    [root@localhost ~]# ls -l /etc/systemd/system/cloud-init.target.wants/
    total 0
    lrwxrwxrwx. 1 root root 44 May 17 05:15 cloud-config.service -> /usr/lib/systemd/system/cloud-config.service
    lrwxrwxrwx. 1 root root 43 May 17 05:15 cloud-final.service -> /usr/lib/systemd/system/cloud-final.service
    lrwxrwxrwx. 1 root root 48 May 17 05:15 cloud-init-local.service -> /usr/lib/systemd/system/cloud-init-local.service
    lrwxrwxrwx. 1 root root 42 May 17 05:15 cloud-init.service -> /usr/lib/systemd/system/cloud-init.service
    
    ## cloud-init.target
    # /usr/lib/systemd/system/cloud-init.target
    # cloud-init target is enabled by cloud-init-generator
    # To disable it you can either:
    #  a.) boot with kernel cmdline of 'cloud-init=disabled'
    #  b.) touch a file /etc/cloud/cloud-init.disabled
    [Unit]
    Description=Cloud-init target
    After=multi-user.target
    
    # 18.2
    [root@localhost multi-user.target.wants]# ls -l
    total 0
    lrwxrwxrwx. 1 root root 44 Dec  5  2018 cloud-config.service -> /usr/lib/systemd/system/cloud-config.service
    lrwxrwxrwx. 1 root root 43 Dec  5  2018 cloud-final.service -> /usr/lib/systemd/system/cloud-final.service
    lrwxrwxrwx. 1 root root 48 Dec  5  2018 cloud-init-local.service -> /usr/lib/systemd/system/cloud-init-local.service
    lrwxrwxrwx. 1 root root 42 Dec  5  2018 cloud-init.service -> /usr/lib/systemd/system/cloud-init.service
    
    ```
  
  + 18.5多了一个`system-generators`下的脚本，这个脚本根据是否能找到`datasource`决定`cloud-init`服务是否启动：
  
    ```bash
    # /usr/lib/systemd/system-generators/cloud-init-generator
    ...
        # enable AND ds=found == enable
        # enable AND ds=notfound == disable
        # disable || <any> == disabled
        if [ "$result" = "$ENABLE" ]; then
            debug 1 "checking for datasource"
            check_for_datasource
            ds=$_RET
            if [ "$ds" = "$NOTFOUND" ]; then
                debug 1 "cloud-init is enabled but no datasource found, disabling"
                result="$DISABLE"
            fi
        fi
    ...
    ```
  
    + 如果没有找到数据源，就会把已经`enable`的服务再`disable`（就是把链接文件删掉）
    
    ```bash
        elif [ "$result" = "$DISABLE" ]; then
            if [ -f "$link_path" ]; then
                if rm -f "$link_path"; then
                    debug 1 "disabled. removed existing $link_path"
                else
                    ret=$?
                    debug 0 "[$ret] disable failed, remove $link_path"
                fi
            else
                debug 1 "already disabled: no change needed [no $link_path]"
            fi
            if [ -e "$RUN_ENABLED_FILE" ]; then
                rm -f "$RUN_ENABLED_FILE"
            fi
        else
            debug 0 "unexpected result '$result' 'ds=$ds'"
            ret=3
        fi
        return $ret
    ```
    
    
    > 参考：https://forums.opensuse.org/t/cloud-init-does-not-run/131727/7

## 解决方法

### 1

+ 最简单的办法是改成和18.2一样的方式，让四个服务依附于`multi-user.target`启动

### 2

+ `cloud-init-generator`脚本中在查找数据源的时候，会调用`/usr/libexec/cloud-init/ds-identify`脚本，这个脚本大概的功能，是检查`ds-identify`配置文件，在这个配置文件中，可以通过自定义策略来改变默认策略，达到控制服务启动的作用。

```bash
# shellcheck disable=2015,2039,2162,2166,3043
#
# ds-identify is configured via /etc/cloud/ds-identify.cfg
# or on the kernel command line. It takes the following inputs:
#
# datasource: can specify the datasource that should be used.
#   kernel command line option: ci.datasource=<dsname> or ci.ds=<dsname>
#   example line in /etc/cloud/ds-identify.cfg:
#      datasource: Ec2
#
# policy: a string that indicates how ds-identify should operate.
#
#   The format is:
#        <mode>,found=value,maybe=value,notfound=value
#   default setting is:
#     search,found=all,maybe=all,notfound=disabled
#
#   kernel command line option: ci.di.policy=<policy>
#   example line in /etc/cloud/ds-identify.cfg:
#      policy: search,found=all,maybe=none,notfound=disabled
```

+ 新建`/etc/cloud/ds-identify.cfg`，在其中写入：

  ```
  policy: search,found=all,maybe=none,notfound=enabled
  ```

+ `notfound`被改为`enabled`，即便没有找到数据源，`cloud-init`也可以正常启动。