# Zabbix学习



## zabbix_server

### zabbix housekeeping

+ housekeeping的作用是删除数据库中的过期数据。
+ 启用housekeeper需要在zabbix_server运行时添加-R housekeeper_execute执行，此选项可以忽略正在进行中的管家程序。（-R为运行时控制选项）
+ 可以在web页面上对housekeeping选项做设置。
+ **运行时控制不支持openbsd和netbsd系统。**

### zabbix进程用户

+ Zabbix server 允许使用非 root 用户运行。它将以任何非 root 用户的身份运行。因此，使用非 root 用户运行 server 是没有任何问题的。
+ 如果你试图以“root”身份运行它，它将会切换到一个已经“写死”的“zabbix”用户，可以修改 Zabbix server 配置文件中的“AllowRoot”参数，则可以只以“root”身份运行 Zabbix server。
+ 如果 Zabbix server 和 agent均运行在同一台服务器上，建议使用不同的用户运行 server 和 agent 。否则,，如果两者都以相同的用户运行，Agent 可以访问 Server 的配置文件, 任何 Zabbix 管理员级别的用户都可以很容易地检索到 Server 的信息。例如，数据库密码。

## zabbix_agent

+ agent可以进行被动检查和主动检查，取决于监控项的类型“Zabbix agent或Zabbix agent（active）”
+ 32位的zabbix agent可以运行在64位系统上，但在某些情况下可能会失败。
+ agent的运行时控制只有日志级别的设定，且不支持openbsd，netbsd和windows。
+ agent在UNIX系统上可以以非root用户运行，如果以root身份运行，它将会切换到zabbix用户，可以在配置文件中修改“AllowRoot”参数来允许以root用户运行。
+ 2.2版本以前，zabbix agent在成功退出时返回0，异常时返回255，2.2及更高的版本，成功退出返回0，异常返回1。

## zabbix_proxy

+ proxy可以代表server工作，将从受监控设备采集到的数据缓存在本地，然后传输到所属的server上。
+ proxy是可选的，有利于分担单个server的负载。如果只有代理采集数据，server的cpu和磁盘I/O的开销可以降低。
+ proxy无需本地管理员即可集中监控远程位置、分支机构和网络的理想解决方案。
+ proxy需要使用独立的数据库。支持SQLite、MySQL、PostgreSQL。使用Oracle和DB2可能会有风险，如自动发现规则中的遇到问题返回值。
+ proxy的运行时控制选项和server相同。

## zabbix_sender和zabbix_get

+ server和agnet之间通讯的命令行应用程序，通常用于故障排错或脚本。

## zabbix自动注册

+ 可以使活动的agent自动注册到服务器上，而不需要手动在服务器上进行配置。

+ 当以前未知的active agent要求检查时，会发生自动注册。

+ active agent支持对被添加的主机进行被动检查的监控，在agent要求检查时，需要提供配置文件中的“ListenIP”或“ListenPort”字段，将参数发给服务器（多个IP发送到第一个）。

+ agent需要在配置文件中指定“ServerActive”参数。

+ 服务器从agent收到注册请求时，会调用一个动作（Action），事件源自动注册（Auto-Registion）必须配置为agent自动注册。

  + 在web页面上，进入“配置->动作”，选择事件源为自动注册，然后新建。
  + 定义动作名称，指定“主机元数据”。元数据一般会发送主机名，但为了便于区分主机，可以选择其他信息。主机元数据在agent配置文件中，有两种“HostMetadata”和“HostMetadataItem”。
  + 在“操作”选项卡中，添加“添加主机”，“添加到主机组”，“链接到模板”等。

  
