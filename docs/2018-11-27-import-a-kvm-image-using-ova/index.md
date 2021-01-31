# kvm使用ova导入虚拟机镜像


+ 从virtualbox打包来的ova格式镜像，发现无法在kvm上直接使用，会提示镜像无法引导，因为kvm使用的虚拟磁盘格式多数都是qcow2的，所以应该可以将ova转成该格式。
+ 其实ova格式是使用tarball打包的，用file命令就可以验证。

```bash
~ $ file Evergreen_trunk_Squeeze.ova
Evergreen_trunk_Squeeze.ova:                POSIX tar archive (GNU)
```

+ 所以直接解压文件就可以，解压后一般会得到一个原来的磁盘格式和一个ovf文件，qemu自带工具就可以转换格式。

``` bash
~ $ qemu-img convert -O qcow2 Evergreen_trunk_Squeeze-disk1.vmdk Evergreen_trunk_Squeeze.qcow2
```


