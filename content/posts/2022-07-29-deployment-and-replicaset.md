---

title: "k8s的Deployment与replicaSet"
date: 2022-07-29T00:00:00+08:00
toc: true
tags: ["kubernetes"]
categories: ["饭碗"]

---

## Deployment

- 一个 Deployment 为 [Pod](https://kubernetes.io/docs/concepts/workloads/pods/pod-overview/) 和 [ReplicaSet](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/replicaset/) 提供声明式的更新能力。
- Deployment 不直接控制 Pods, 而是通过 ReplicaSet 来间接管理 Pods。
- Deployments 的典型用例： 
   - 创建 Deployment 以将 ReplicaSet 上线。 ReplicaSet 在后台创建 Pods。 检查 ReplicaSet 的上线状态，查看其是否成功。
   - 通过更新 Deployment 的 PodTemplateSpec，声明 Pod 的新状态 。 新的 ReplicaSet 会被创建，Deployment 以受控速率将 Pod 从旧
   - ReplicaSet 迁移到新 ReplicaSet。 每个新的 ReplicaSet 都会更新 Deployment 的修订版本。
   - 如果 Deployment 的当前状态不稳定，回滚到较早的 Deployment 版本。 每次回滚都会更新 Deployment 的修订版本。
   - 扩大 Deployment 规模以承担更多负载。
   - 暂停 Deployment 以应用对 PodTemplateSpec 所作的多项修改， 然后恢复其执行以启动新的上线版本。
   - 使用 Deployment 状态来判定上线过程是否出现停滞。
   - 清理较旧的不再需要的 ReplicaSet 。

```yaml
# Deployment的定义
apiVersion: apps/v1  # 版本号
kind: Deployment  # 类型
metadata:    # 元数据
  name:    # 名称
  namespace:   # 所属命名空间
  labels:   # 标签
    app: 
spec:   # 详情描述
  replicas:  # 定义replicasset负责的副本数量，默认是1
  revisionHistoryLimit: # 保留历史版本，默认是10
  paused: # 暂停部署，默认是false
  progressDeadlineSeconds: # 部署超时时间(s)，默认是600
  strategy: # 策略
    type: RollingUpdates  # 滚动更新策略
    rollingUpdate:  # 滚动更新
      maxSurge: # 最大额外可以存在的副本数，可以为百分比，也可以为整数
      maxUnavaliable: # 最大不可用状态的pod的最大值，可以为百分比，也可以为整数
  selector:  # 选择器，通过它指定该控制器管理哪些pod
    matchLabels:   # Labels匹配规则
       app: nginx-pod
    matchExpressions:   # Expression匹配规则
      - {key: app, operator: In, values: [nginx-pod]}
  template:  # 模板，当副本数量不足时，会根据下面的模板创建pod副本
    metadata:
        labels:
          app: nginx-pod
    spec:
      containers:
      - name: nginx
        image: nginx:1.17.1
        ports:
        - containerPort: 80
```

> -  在 API `apps/v1`版本中，`.spec.selector` 和 `.metadata.labels` 如果没有设置的话， 不会被默认设置为 `.spec.template.metadata.labels`，所以需要明确进行设置。 同时在 `apps/v1`版本中，Deployment 创建后 `.spec.selector` 是不可变的。 
> -  `.spec.selector` 必须匹配 `.spec.template.metadata.labels`，否则请求会被 API 拒绝。 
> -  `.spec` 中只有 `.spec.template` 和 `.spec.selector` 是必需的字段 


## ReplicaSet

- ReplicaSet 的目的是维护一组在任何时候都处于运行状态的 Pod 副本的稳定集合。 因此，它通常用来保证给定数量的、完全相同的 Pod 的可用性。
- ReplicaSet 是通过一组字段来定义的，包括一个用来识别可获得的 Pod 的集合的选择算符、一个用来标明应该维护的副本个数的数值、一个用来指定应该创建新 Pod 以满足副本个数条件时要使用的 Pod 模板等等。 每个 ReplicaSet 都通过根据需要创建和删除 Pod 以使得副本个数达到期望值， 进而实现其存在价值。当 ReplicaSet 需要创建新的 Pod 时，会使用所提供的 Pod 模板。
- ReplicaSet 通过 Pod 上的 [metadata.ownerReferences](https://kubernetes.io/zh-cn/docs/concepts/architecture/garbage-collection/#owners-and-dependents) 字段连接到附属 Pod，该字段给出当前对象的属主资源。 ReplicaSet 所获得的 Pod 都在其 ownerReferences 字段中包含了属主 ReplicaSet 的标识信息。正是通过这一连接，ReplicaSet 知道它所维护的 Pod 集合的状态， 并据此计划其操作行为。
- ReplicaSet 使用其选择算符来辨识要获得的 Pod 集合。如果某个 Pod 没有 OwnerReference 或者其 OwnerReference 不是一个[控制器](https://kubernetes.io/zh-cn/docs/concepts/architecture/controller/)， 且其匹配到某 ReplicaSet 的选择算符，则该 Pod 立即被此 ReplicaSet 获得。

> 官方建议：不要直接使用或操作 ReplicaSet，而是使用 Deployment 来管理。


```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: frontend
  labels:
    app: guestbook
    tier: frontend
spec:
  # 按你的实际情况修改副本数
  replicas: 3
  selector:
    matchLabels:
      tier: frontend
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      containers:
      - name: php-redis
        image: gcr.io/google_samples/gb-frontend:v3
```
