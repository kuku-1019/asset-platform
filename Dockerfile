# 1. 找个底子：用 Python 3.9 的官方镜像
FROM python:3.9-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 先把清单拷进去，并安装依赖 (用清华源加速)
COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 把剩下所有代码拷进去
COPY . .

# 5. 告诉 Docker 我们要用 8000 端口
EXPOSE 8000

# 6. 启动命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]