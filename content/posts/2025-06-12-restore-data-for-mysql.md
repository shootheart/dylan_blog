---
id: 通过mysql的binlog恢复UPDATE误操作数据
aliases: []
tags:
  - 数据库
categories:
  - 饭碗
date: 2025-06-12T00:00:00+08:00
draft: false
hiddenFromHomePage: false
hiddenFromSearch: false
lastmod: 2025-06-12T00:00:00+08:00
title: 通过mysql的binlog恢复UPDATE误操作的数据
toc: true
---


## 问题起因

因为一个OpenStack虚拟机映射存储卷错误的问题，需要修改 `nova` 数据库的 `block_device_mapping` 表，然后操作 `UPDATE` 忘了加 `WHERE`，把整个表都修改了，4000多条数据，无语。。

![](https://dylanblog.oss-cn-beijing.aliyuncs.com/2025-06-12-restore-data-for-mysql/image-20250613172308274.png)

不知所措的时候突然想起数据库开了binlog，想着是不是能把数据恢复回来。

![](https://dylanblog.oss-cn-beijing.aliyuncs.com/2025-06-12-restore-data-for-mysql/image-20250613172118263.png)

## 尝试恢复

找到了当前的binlog文件，转换成伪sql代码看看：

```
mysqlbinlog --no-defaults --base64-output=DECODE-ROWS -v mysql-bin.000532 > /tmp/binlog.sql
```

> --no-defaults选项是因为报错：unknown variable 'default-character-set=utf8'

命令说明：

```
mysqlbinlog   【参数 】 【binlog文件】  
 
-d, --database=name        仅显示指定数据库的转储内容。
-o, --offset=#            跳过前N行的日志条目。
-r, --result-file=name        将输入的文本格式的文件转储到指定的文件。
-s, --short-form        使用简单格式。
--set-charset=name              在转储文件的开头增加'SET NAMES character_set'语句。
--start-datetime=name        日志的起始时间。
--stop-datetime=name        日志的截止时间。
-j, --start-position=#        日志的起始位置。
--stop-position=#        日志的截止位置。
--base64-output=#        输出语句的base64解码 
    分为三类：
    默认是值auto ,仅打印base64编码的需要的信息，如row-based 事件和事件的描述信息。
    never 仅适用于不是row-based的事件
    decode-rows 配合--verbose选项一起使用解码行事件到带注释的伪SQL语句
-v,--verbose ：显示statement模式带来的sql语句
```


找到了执行批量 `UPDATE` 命令所在的position：

![](https://dylanblog.oss-cn-beijing.aliyuncs.com/2025-06-12-restore-data-for-mysql/image-20250613171121980.png)

![](https://dylanblog.oss-cn-beijing.aliyuncs.com/2025-06-12-restore-data-for-mysql/image-20250613171848552.png)

> 即便是同时执行的许多条`UPDATE`语句，每条语句也都有自己的position，而且positions是聚集在了一起。

之后将这一时间段的`UPDATE`语句导出为sql：

```
mysqlbinlog --nodefaults --base64-output=DECODE-ROWS -v --start-position=565895847 --stop-position=572557706 mysql-bin.000532 > /tmp/recovery.sql
```

> stop-position应该是当前命令执行完的位置，也就是下一条命令执行前的位置。

## 处理sql脚本

```sql
### UPDATE `nova`.`block_device_mapping`
### WHERE
###   @1=2025-06-09 04:15:57
###   @2=2025-06-09 04:15:58
###   @3=NULL
###   @4=22948
###   @5='/dev/vdb'
###   @6=0
###   @7=NULL
###   @8='227e9cba-1ae1-4bac-990c-6f55aa803554'
###   @9=2000
###   @10=NULL
...
### SET
###   @1=2025-06-09 04:15:57
###   @2=2025-06-09 04:15:58
###   @3=NULL
###   @4=22948
###   @5='/dev/vdb'
###   @6=0
###   @7=NULL
###   @8='227e9cba-1ae1-4bac-990c-6f55aa803554'
###   @9=2000
###   @10=NULL
```

现在得到的只是带有注释的伪sql语句，而且它所记录的是当时你所做的`UPDATE`操作的再现，并不是我们想要的恢复数据的语句，所以还需要对这个脚本做额外处理。

网上找到的几个案例应该都是根据自身的情况做了些改动，另外获取原始sql的方法也不一样，所以还是针对现在的问题自己来想办法。

处理这个脚本的思路：去除注释和无用的信息、转换WHERE和SET（恢复原来的数据）、将脚本中的“@1、@2、@3...”替换为实际的字段名、处理字段值的格式（例如字符串和日期的引号等等）。

去除注释和替换字段名基本上可以手动修改，对于4000多条数据，转换WHERE和SET与处理字段值的格式会比较麻烦。于是找来ChatGPT帮我写了两个awk：（两个是因为没有一次成功）

```awk
# update1.awk
# 匹配 UPDATE 行，初始化新一个块
/^### UPDATE `nova`.`block_device_mapping`/ {
    flush(); # 如果有上一块未输出，先输出
    update_line = $0;
    where_block = "";
    set_block = "";
    state = "";
    in_block = 1;
    next;
}

# 进入 WHERE 部分
in_block && /^### WHERE/ {
    state = "WHERE";
    next;
}

# 进入 SET 部分
in_block && /^### SET/ {
    state = "SET";
    next;
}

# 读取 WHERE 或 SET 数据内容
in_block && /^###   @/ {
    if (state == "WHERE") where_block = where_block $0 "\n";
    else if (state == "SET") set_block = set_block $0 "\n";
    next;
}

# 读取到新的块前的空行，判断是否需要输出
in_block && !/^###/ {
    flush();
    in_block = 0;
    next;
}

# 最后一块可能没有触发 flush
END {
    flush();
}

# 函数：输出逆向 SQL
function flush() {
    if (update_line != "") {
        print update_line;
        print "### WHERE";
        printf "%s", set_block;
        print "### SET";
        printf "%s", where_block;
        print ""; # 空行隔开
        update_line = "";
        where_block = "";
        set_block = "";
    }
}
```

```awk
# update2.awk
BEGIN {
  FS = "\n";
  RS = "";  # 每个块之间空行分隔
}

{
  table = "";
  set_block = "";
  where_block = "";
  in_set = 0;
  in_where = 0;

  for (i = 1; i <= NF; i++) {
    line = $i;

    if (line ~ /^UPDATE /) {
      table = line;
    } else if (line ~ /^WHERE$/) {
      in_where = 1;
      in_set = 0;
    } else if (line ~ /^SET$/) {
      in_where = 0;
      in_set = 1;
    } else if (in_where) {
      gsub(/^[ \t]+/, "", line);
      if (line ~ /NULL$/) {
        sub(/=[ \t]*NULL$/, " IS NULL", line);
      }
      where_block = where_block line " AND\n";
    } else if (in_set) {
      gsub(/^[ \t]+/, "", line);
      set_block = set_block line ",\n";
    }
  }

  # 去掉最后的 AND / 逗号
  sub(/ AND\n$/, "", where_block);
  sub(/,\n$/, "", set_block);

  # 打印新 SQL
  print table;
  print "SET";
  print set_block;
  print "WHERE";
  print where_block ";";
  print "";  # 输出块之间空行
}
```

我的整个脚本处理过程大致为：

```bash
# 1. 执行第一个脚本
awk -f update1.awk recovery.sql > recovery_1.sql

# 2. 手动去除注释，替换字段名

# 3. 执行第二个脚本
awk -f update2.awk recovery_1.sql > recovery_2.sql
```

处理完的sql脚本效果：

```sql
UPDATE `nova`.`block_device_mapping`
SET
created_at=2025-06-09 04:15:57,
updated_at=2025-06-09 04:15:58,
deleted_at=NULL,
id=22948,
device_name='/dev/vdb',
delete_on_termination=0,
snapshot_id=NULL,
volume_id='227e9cba-1ae1-4bac-990c-6f55aa803554',
volume_size=2000,
no_device=NULL,
connection_info='{"driver_volume_type": "rbd", "connector": {"platform": "x86_64", "host": "compute15", "do_local_attach": false, "ip": "10.241.101.17", "os_type": "linux2", "multipath": false, "initiator": "iqn.1994-05.com.redhat:525faaefdd3a"}, "serial": "227e9cba-1ae1-4bac-990c-6f55aa803554", "data": {"secret_type": "ceph", "name": "data01/volume-227e9cba-1ae1-4bac-990c-6f55aa803554", "encrypted": false, "cluster_name": "icfs01", "secret_uuid": "7a09d376-d794-499d-ab39-fadcf47b5158", "qos_specs": null, "hosts": ["10.241.101.200", "10.241.101.201", "10.241.101.202"], "volume_id": "227e9cba-1ae1-4bac-990c-6f55aa803554", "auth_enabled": true, "access_mode": "rw", "auth_username": "lc01", "ports": ["6789", "6789", "6789"]}}',
instance_uuid='84e3f70b-a264-4056-b20b-8817b3d38cd2',
deleted=0,
source_type='volume',
destination_type='volume',
guest_format=NULL,
device_type=NULL,
disk_bus=NULL,
boot_index=NULL,
image_id=NULL,
tag=NULL,
attachment_id=NULL
WHERE
created_at=2025-06-09 04:15:57 AND
updated_at=2025-06-09 04:15:58 AND
deleted_at IS NULL AND
id=22948 AND
device_name='/dev/vdb' AND
delete_on_termination=0 AND
snapshot_id IS NULL AND
volume_id='227e9cba-1ae1-4bac-990c-6f55aa803554' AND
volume_size=2000 AND
no_device IS NULL AND
connection_info='{"driver_volume_type": "iscsi", "connector": {"initiator": "iqn.1994-05.com.redhat:525faaefdd31", "ip": "10.241.101.37", "platform": "x86_64", "host": "compute31", "do_local_attach": false, "os_type": "linux2", "multipath": false}, "serial": "4d48a5aa-8fe5-40f6-84af-f3a406a5641e", "data": {"device_path": "/dev/sdu", "target_discovered": false, "encrypted": false, "qos_specs": null, "target_iqn": "iqn.2001-01.com.sugon:storage.target.10.241.101.184", "target_portal": "10.241.101.184:3260", "volume_id": "4d48a5aa-8fe5-40f6-84af-f3a406a5641e", "target_lun": 2, "access_mode": "rw"}}' AND
instance_uuid='84e3f70b-a264-4056-b20b-8817b3d38cd2' AND
deleted=0 AND
source_type='volume' AND
destination_type='volume' AND
guest_format IS NULL AND
device_type IS NULL AND
disk_bus IS NULL AND
boot_index IS NULL AND
image_id IS NULL AND
tag IS NULL AND
attachment_id IS NULL;
```


但是这两个脚本并没有很好处理datetime类型的字段值，所以我索性将这几个datetime的字段值删掉了，因为比对了一下值没有变，没有影响。

## 恢复数据

找来一个测试环境，导入当前错误的表数据，测试这个导入脚本。随机找几条数据，和现有环境的数据对比一下（格式之类的）。

测试没问题，再备份当前生产环境的所有数据，恢复生产数据库。

```bash
# 备份当前所有数据
mysqldump -u root -p --all-databases --default-character-set=utf8 > all-20250612.sql

# 恢复数据
mysql -u root -p -D nova < restore2_3.sql
```

最后找几台测试虚拟机关机重启来试试，确保卷没有错。


## 注意

未验证网上的多数博客所提到的，直接通过`mysqlbinlog`导出sql，然后直接就导入数据库的方法，不同的问题应该是使用不同的方法。


## 参考

https://www.cnblogs.com/mimeng/p/17090952.html

https://www.cnblogs.com/gomysql/p/3582058.html

https://blog.csdn.net/jkzyx123/article/details/127094632
