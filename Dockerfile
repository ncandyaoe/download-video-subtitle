# 使用官方的 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖，比如 ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# 将依赖文件复制到工作目录
COPY ./requirements.txt /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将项目代码复制到工作目录
COPY . /app/

# 暴露端口，让外界可以访问
EXPOSE 7878

# 定义容器启动时运行的命令
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7878"] 