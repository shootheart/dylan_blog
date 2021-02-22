# WSL文件权限问题


## 问题起因

+ 在wsl上欲通过rsync的ssh方式进行文件同步，ssh密钥文件的权限是不能过于开放的，所以需要在wsl下将密钥文件的权限修改成只有文件所有者有读写权限。
+ 但是实际操作发现，在wsl下无论使用文件所有者还是root用户，都不能通过chmod命令修改文件的权限，这无疑是一个比较严峻的问题。

## 测试

+ 在搜索了一些网络博客后得知，wsl下的文件权限与windows上的文件权限是相关的。由此我们来进行一个测试。
+ 我们在wsl下新建一个文件，可以看到文件和目录的默认权限都为777。

  ![image-20210205162607575](https://dylanblog.oss-cn-beijing.aliyuncs.com/2021-02-09-the-file-permissions-of-wsl/image-20210205162607575.png "wsl下新建文件")

+ 当我们在windows下将这个文件修改为所有者只读，在wsl中的权限会变成444（为什么会是444呢？）。

  ![image-20210207140731598](https://dylanblog.oss-cn-beijing.aliyuncs.com/2021-02-09-the-file-permissions-of-wsl/image-20210207140731598.png "文件权限修改为所有者只读")

  ![image-20210207141132171](https://dylanblog.oss-cn-beijing.aliyuncs.com/2021-02-09-the-file-permissions-of-wsl/image-20210207141132171.png "wsl中的权限变成444")

+ 也就是说在wsl下，所有者、用户组和其它用户这三者的权限是同时变化的，这依旧不能解决我们的问题。


+ 那么是否有办法让wsl可以像普通的linux系统一样，可以任意修改文件权限呢？微软当然考虑到了，就是配置wsl元数据。

## 解决

### WSL元数据

+ wsl元数据可以通过配置文件wsl.conf装载，使windows文件拥有扩展属性并对其进行解释，最终达到的效果就是文件在wsl上拥有独立的文件系统权限。

  {{< admonition note "解释一下上面测试的结果" >}}

  如果没有配置wsl元数据，文件权限是按照windows当前用户的文件权限进行转换，且对用户、组和其它用户赋予相同的值。比如文件在windows当前用户下的权限是文件所有者只读，在wsl下就会显示为444权限，这也就是为什么我们上边测试文件的权限会变成444。

  {{< /admonition >}}

### 配置WSL元数据

+ wsl.conf文件位于wsl的/etc目录下，如果没有的话可以自行新建，该文件格式不正确或缺失不影响wsl正常启动。

+ 以下是官方文档给出的示例：

  ```ini
  # Enable extra metadata options by default
  # umask和fmask用于设置权限掩码，这两个掩码作用于文件时会做“或”运算，以最终结果赋予文件权限
  [automount]
  enabled = true
  root = /windir/
  options = "metadata,umask=22,fmask=11"
  mountFsTab = false
  
  # Enable DNS – even though these are turned on by default, we'll specify here just to be explicit.
  [network]
  generateHosts = true
  generateResolvConf = true
  ```

+ 文件保存后重新启动wsl，再看我们刚才创建的文件，变成了744。没错，是我们配置文件中写的umask(022)和fmask(011)或运算后得到的反掩码的权限。

  ![image-20210209112434418](https://dylanblog.oss-cn-beijing.aliyuncs.com/2021-02-09-the-file-permissions-of-wsl/image-20210209112434418.png "文件权限变成744，umask和fmask或运算的结果")
  
  {{< admonition tip "重启wsl的方法" >}}
  
  每次打开wsl/ubuntu都会在系统后台添加一个进程，开始以为只要杀掉这个进程就可以完美实现子系统的重启，但实际测试并不能，进入wsl后查看uptime依然是上次重启后的运行时间。
  
  如何可以真正重启wsl呢？这里涉及到了一个服务：LxssManager。wsl是基于这个服务运行的，所以只需要重启这个服务，就可以实现wsl的完美重启啦。
  
  你可以选择在管理员cmd中执行net stop/start LxssManager来重启，也可以在service.msg里找到这个服务重启。
  
  {{< /admonition >}}
  
+ 既然wsl元数据已经配置成功了，也就是说文件在wsl下拥有了独立的文件权限，我们就可以通过chmod命令随意设置文件权限了。我们把需要修改的ssh私钥文件修改成600权限，再尝试用密钥登录服务器，显示成功！

  ![image-20210209114652593](https://dylanblog.oss-cn-beijing.aliyuncs.com/2021-02-09-the-file-permissions-of-wsl/image-20210209114652593.png "完美解决")


{{< admonition quote "参考文档" >}}

有关WSL元数据的相关信息： https://docs.microsoft.com/zh-cn/windows/wsl/file-permissions#wsl-metadata-on-windows-files

{{< /admonition >}}
