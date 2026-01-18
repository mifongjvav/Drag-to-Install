# Drag-to-Install

一个模仿macOS安装逻辑的安装器

## 安装库

执行以下代码：
```shell
pip install wxPython
pip install pyinstaller
```

## 如何构建成exe

### 包含eula

```shell
pyinstller --onefile --windowed --name "名字" --icon "app.png" --add-data "app.png;." --add-data "app.zip;." --add-data "eula.txt;." Main.py
```

### 不包含eula

```shell
pyinstller --onefile --windowed --name "名字" --icon "app.png" --add-data "app.png;." --add-data "app.zip;." Main.py
```

## 警告

你需要保证你的工作目录下有`app.png`，`app.zip`，`eula.txt`（可选）才可以构建
