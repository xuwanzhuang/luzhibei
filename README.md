# 火点/烟雾目标检测 Web 应用

## 环境
- 运行时：conda 环境 `aigc`（Python 3.12）
- 解释器路径：`D:\miniconda\envs\aigc\python.exe`
- 依赖：见 `requirements.txt`

## 安装依赖
```bash
& "D:\miniconda\envs\aigc\python.exe" -m pip install -r requirements.txt
```

## 模型
- 将已训练权重放入 `models/`，并在 `app/config.py` 中把 `MODEL_PATH` 指向该文件。
- 权重缺失时应用仍可启动，检测接口会返回 503 与可理解提示。

## 启动
```bash
& "D:\miniconda\envs\aigc\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 访问
浏览器打开 `http://localhost:8000`

## 测试
```bash
& "D:\miniconda\envs\aigc\python.exe" -m pytest -v
```

## 免责声明
检测结果仅用于辅助识别，不能替代人工复核和实际应急决策。
