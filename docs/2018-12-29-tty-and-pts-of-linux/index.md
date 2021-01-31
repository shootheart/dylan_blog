# Linux系统中的tty与pts


### 问题

+ centos7中没有pts/0和pts/3？

### tty、pty与pts的概念

+ tty（终端设备的统称）
  + tty源于Teletypes，原指电传打字机，现在指终端比较合适（应该是属于终端设备）
+ pty（虚拟终端）
  + 当使用远程到主机的时候，就需要用到虚拟终端
+ pts/ptmx（pts/ptmx结合使用，进而实现pty）
  + pts（pseudo-terminal slave）是pty的实现方法，和ptmx（pesude-terminal master）配合使用实现pty
