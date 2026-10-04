# MiniJEV Docker镜像

FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV JEV_MODEL=glm-4.5-flash

# 运行演示
CMD ["python", "demo.py"]
