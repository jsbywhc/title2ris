# Title2RIS Converter v1.0.4

## 概述

Title2RIS 是一个简单的自用小程序，用于将学术论文标题转换为 RIS 格式的工具，利用 Crossref API 获取论文元数据。该工具旨在简化文献管理流程，特别适合需要批量导入参考文献到文献管理软件的研究人员。

## 功能特点

- 从文本文件批量读取论文标题
- 并行处理支持，可配置并发数量
- 通过 Crossref API 自动检索论文元数据
- 将检索结果转换为标准 RIS 格式
- 强大的错误处理机制，包括超时重试逻辑
- 支持部分结果保存，避免因单个错误中断整个处理流程
- 命令行参数支持，提高灵活性和易用性
- 可配置的 API 设置和日志参数
- 详细的日志记录，便于故障排查和使用跟踪

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
- 详细的日志记录，记录所有操作和错误信息

## 工作原理

Title2RIS 的工作流程如下：

1. **标题读取**：从输入文本文件中按行读取论文标题
2. **元数据检索**：
   - **并行处理** (v1.0.4)：使用 `ThreadPoolExecutor` 同时发起多个 API 请求，由 `RateLimiter` 协调请求频率，避免触发 API 限制。
   - 将每个标题进行 URL 编码，构造 Crossref API 查询请求
   - 发送 HTTP 请求到 Crossref API（`https://api.crossref.org/works`）
   - 处理 API 响应，提取相关元数据（如作者、期刊、出版年份等）
   - **特殊标题处理** (v1.0.1-v1.0.2)：
      - 自动跳过各种补充信息条目（如 Supplementary Information, SI 等）
      - 过滤 Frontispiece 条目
      - 如果首个结果是特殊标题，则尝试使用第二个结果
3. **RIS 格式转换**：
   - 将获取的元数据转换为标准 RIS 格式
   - 包含多种标签，如 TY (类型)、TI (标题)、AU (作者)、JF (期刊名)、PY (年份)、DO (DOI) 等
4. **错误处理与日志记录**：
   - 实现指数退避重试逻辑，在网络超时或请求失败时自动重试
   - 单个标题失败不会影响整体处理流程
   - 支持处理中断时保存已完成的结果
   - 通过日志系统记录详细的操作和错误信息

## 配置

从 v1.0.3 开始，Title2RIS 引入了配置文件 `config.py`，支持以下配置：

- API 配置：URL、用户代理、超时设置、重试次数等
- 并行配置 (v1.0.4)：`MAX_WORKERS` 设置并发线程数
- 特殊标题过滤：可配置需要跳过的特殊标题列表
- 文件配置：默认输出文件、文件编码等
- 日志配置：日志格式、日志级别、日志文件等

## 日志系统

v1.0.3 引入了完整的日志系统，通过 `logger.py` 实现，包括：

- 控制台和文件双重日志输出
- 可配置的日志级别和格式
- 详细记录程序执行过程、API 调用结果和错误信息

## 版本历史

- **v1.0**: 初始版本，实现标题到 RIS 的基本转换功能和 Crossref 元数据提取
- **v1.0.1**: 优化处理补充信息的逻辑，支持读取第二个文献条目
- **v1.0.2**: 改进 SI 过滤算法，新增对 Frontispiece 条目的排除
- **v1.0.3**: 添加配置文件和日志系统支持，提升可维护性和用户体验
- **v1.0.4**: 添加并行处理支持，使用 ThreadPoolExecutor 实现多线程 API 请求，显著提升批量处理速度

## 技术实现

- 使用 requests 库与 Crossref API 接口交互，通过 HTTP 请求获取论文元数据
- **并发请求**：使用 `concurrent.futures.ThreadPoolExecutor` 实现多线程异步请求
- **频率限制**：自定义 `RateLimiter` 类，确保在多线程环境下遵守 API 访问频率限制
- 采用 Python 标准库进行文件处理和命令行参数解析
- 实现了指数退避的智能重试机制以应对网络不稳定情况
- 使用 Python 日志模块记录程序执行情况

## 许可

MIT

## 说明

这只是一个自用的小程序，功能非常简单，主要是为了满足个人需求而开发的工具。欢迎根据自己的需求进行修改和定制。

## 联系方式

如有问题或建议，请提交 issue 或联系项目维护者。
