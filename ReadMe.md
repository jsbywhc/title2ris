# Title2RIS Converter v1.0.0

## 概述

Title2RIS 是一个用于将学术论文标题转换为 RIS 格式的工具，利用 Crossref API 获取论文元数据。该工具旨在简化文献管理流程，特别适合需要批量导入参考文献到文献管理软件的研究人员。

## 功能特点

- 从文本文件批量读取论文标题
- 通过 Crossref API 自动检索论文元数据
- 将检索结果转换为标准 RIS 格式
- 强大的错误处理机制，包括超时重试逻辑
- 支持部分结果保存，避免因单个错误中断整个处理流程
- 命令行参数支持，提高灵活性和易用性

## 安装要求

- Python 3.6+
- requests 库 (用于 Crossref API 交互)

## 安装方法

```bash
pip install -r requirements.txt
```

## 使用方法

基本用法：

```bash
python title2ris.py input.txt output.ris
```

其中：
- `input.txt` 是包含论文标题的文本文件，每行一个标题
- `output.ris` 是生成的 RIS 格式输出文件

## 示例

输入文件 `input.txt` 示例：

```
The structure of scientific revolutions
Artificial intelligence: a modern approach
Machine learning: a probabilistic perspective
```

运行命令：

```bash
python title2ris.py input.txt my_references.ris
```

生成的 `my_references.ris` 文件将包含可导入到文献管理软件（如 Zotero、Mendeley 或 EndNote）的 RIS 格式条目。

## 错误处理

Title2RIS 包含的错误处理机制：

- API 超时时自动重试
- 对于无法找到的标题会生成警告并继续处理其他标题
- 处理过程中断时支持保存已处理的结果

## 工作原理

Title2RIS 的工作流程如下：

1. **标题读取**：从输入文本文件中按行读取论文标题
2. **元数据检索**：
   - 将每个标题进行 URL 编码，构造 Crossref API 查询请求
   - 发送 HTTP 请求到 Crossref API（`https://api.crossref.org/works`）
   - 处理 API 响应（示例参见 `result-example.json`），提取相关元数据（如作者、期刊、出版年份等）
3. **RIS 格式转换**：
   - 将获取的元数据转换为标准 RIS 格式
   - 包含多种标签，如 TY (类型)、TI (标题)、AU (作者)、JF (期刊名)、PY (年份)、DO (DOI) 等
4. **错误处理**：
   - 实现指数退避重试逻辑，在网络超时或请求失败时自动重试
   - 单个标题失败不会影响整体处理流程
   - 支持处理中断时保存已完成的结果

## 技术实现

- 使用 requests 库与 Crossref API 接口交互，通过 HTTP 请求获取论文元数据
- 采用 Python 标准库进行文件处理和命令行参数解析
- 实现了指数退避的智能重试机制以应对网络不稳定情况

## 许可

MIT

## 联系方式

如有问题或建议，请提交 issue 或联系项目维护者。