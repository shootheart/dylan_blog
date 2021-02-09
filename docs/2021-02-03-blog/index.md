# github+Typora博客搭建方案


## 环境

+ 平台：github pages
+ 框架：hugo
+ 主题：LoveIt
+ 编辑器：Typora

## 搭建记录

{{< admonition quote >}}

完整搭建文档可参考：https://hugoloveit.com/zh-cn/

{{< /admonition >}}

### 本地安装hugo

> Hugo是由Go语言实现的静态网站生成器。简单、易用、高效、易扩展、快速部署。

+ Hugo需要先安装Go语言环境

+ 在官方github仓库下载对应操作系统的Hugo的zip包

+ 将下载好的zip包解压到Go安装目录的bin目录下

+ Hugo 提供了一个 `new` 命令来创建一个新的网站

  ```bash
  hugo new site my_website
  cd my_website
  ```


### 导入主题

+ github上下载最新版LoveIt主题：https://github.com/dillonzq/LoveIt.

+ 下载好的zip包解压到`my_website`下的`themes`目录

  {{< admonition note "注意" >}}config.toml里的theme参数要和主题目录的名称一致，否则在构建网站时会报错{{< /admonition >}}

### 配置网站

+ 编写`my_website`下的config.tmol文件
+ 可以参考官方给出的例子：https://hugoloveit.com/zh-cn/theme-documentation-basics/#basic-configuration

### 构建本地网站

```bash
hugo serve --disableFastRender
# --disableFastRender可以通过hugo的.Scratch来实现实时预览文章效果
```

+ 通过`localhost:1313`可以访问本地搭建的网站
+ 当修改文件时，网站会自动进行更新

### 导入博文

+ 博文的源文件在`my_website`下的content/posts

+ 可以在文章的内容前面加上yaml格式或json格式的元数据参数

  ```yaml
  # 常用
  ---
  title: "文章标题"
  date: 2021-02-03T00:00:00+08:00
  draft: false (是否为草稿，如果在hugo serve中加入了参数--buildDrafts/-D，将决定此篇文章是否显示在主页)
  toc: true (是否启用目录)
  tags: ["blog"] (标签)
  categories: ["生活多美好"] (分类)
  lightgallery: true (是否启用lightgallery)
  ---
  文章正文
  ```

#### 图片链接

+ 

### 推送到github

## 优化

### 配置cdn

### 压缩图片

## 待优化

### 自动化

### 图床


