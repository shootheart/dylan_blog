---

title: "k8s创建pod"
date: 2022-07-29T00:00:00+08:00
toc: true
tags: ["kubernetes"]
categories: ["饭碗"]

---

## 创建pod的流程

<img src="https://cdn.nlark.com/yuque/0/2022/png/12871581/1671095739542-e401f1ca-f879-4f78-8bf2-becd75bf14cc.png" alt="图片.png" referrerPolicy="no-referrer" />



## 创建pod操作

### 使用yaml

```yaml
# 编写yaml
apiVersion: v1
kind: Namespace   # 创建namespace，或不创建使用现有的namespace
metadata:
  name: nginx-test
  labels:
    name: label-nginx

---
apiVersion: v1
kind: Pod
metadata:
  namespace: nginx-test
  name: nginx
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:latest
    imagePullPolicy: Never
    ports:
    - containerPort: 80

apiVersion: apps/v1
kind: Deployment  # 创建deployment
metadata:
  namespace: nginx-test
  name: nginx-deploy
spec:
  selector:
    matchLabels:
      app: nginx
  replicas: 2
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 80
```

```bash
# 执行部署pod
kubectl create -f nginx-deploy.yaml
```

### 使用命令

```bash
kubectl run nginx-2 --image=nginx --image-pull-policy=Never --namespace=nginx-test --port=80
```
