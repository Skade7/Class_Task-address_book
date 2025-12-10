# 📘 Flask 通讯录管理系统 (Address Book Web App)

这是一个基于 Python Flask 框架开发的 Web 通讯录管理系统。它允许用户注册账户，管理个人联系人，支持多维度的联系方式记录、Excel 批量导入导出以及联系人收藏功能。

本项目是 **[EE308FZ软件工程]** 的作业。

## ✨ 功能特性 (Key Features)

本项目实现了以下核心功能：

*   **用户认证系统**：
    *   支持用户注册、登录、注销。
    *   密码使用 Hash 加密存储，保障安全。
    *   支持用户头像上传与管理。
*   **联系人管理 (CRUD)**：
    *   添加、编辑、删除联系人。
    *   **多联系方式支持**：采用了“一对多”数据库设计，一个联系人可以拥有无限多个电话、邮箱、社交账号或地址。
*   **高级功能**：
    *   **⭐ 收藏功能 (Bookmark)**：可一键收藏重要联系人，并支持“仅显示收藏”筛选。
    *   **📊 Excel 导入导出**：
        *   **导出**：利用 Pandas 将联系人数据（自动合并多条记录）导出为 Excel 文件。
        *   **导入**：支持解析特定格式的 Excel 文件，批量添加联系人。
    *   **🔍 搜索功能**：支持按姓名模糊搜索联系人。
*   **响应式 UI**：
    *   使用自定义 CSS 设计，界面整洁，兼容不同屏幕尺寸。
    *   优化的表格布局与交互体验。

## 🛠️ 技术栈 (Tech Stack)

*   **后端**：Python 3.x, Flask
*   **数据库**：SQLite, SQLAlchemy (ORM)
*   **数据处理**：Pandas, OpenPyXL (用于 Excel 处理)
*   **前端**：HTML5, CSS3, Jinja2 模板引擎
*   **表单验证**：Flask-WTF, WTForms

## 📂 项目结构 (Directory Structure)

```text
address_book/
├── instance/
│   └── address_book.db    # SQLite 数据库文件 (自动生成)
├── static/
│   ├── style.css          # 页面样式文件
│   └── uploads/           # 用户上传的头像
├── templates/
│   ├── base.html          # 基础模板 (包含导航栏)
│   ├── index.html         # 首页 (联系人列表/添加/编辑)
│   ├── login.html         # 登录页
│   └── register.html      # 注册页
├── app.py                 # Flask 主程序入口
├── requirements.txt       # 项目依赖库列表
└── README.md              # 项目说明文档

🚀 快速开始 (Installation & Setup)
请按照以下步骤在本地运行本项目：

1. 克隆或下载项目

git clone https://github.com/你的用户名/address_book.git
cd address_book

2. 安装依赖
建议使用 Python 3.8 或以上版本。

pip install -r requirements.txt

3. 运行程序

python app.py

4. 访问应用
打开浏览器，访问：

http://127.0.0.1:5000

提示：首次运行时，你可以直接在注册页面注册一个新账号开始使用。数据库文件包含在 instance/ 文件夹中，如果你想重置数据，可以删除该文件，重启程序后会自动重新生成。
📝 Excel 导入模版说明
如果要使用导入功能，请确保 Excel 文件 (.xlsx) 包含以下列名：
Name (必填)
Phones (可选，多个号码用分号 ; 隔开)
Emails (可选，用分号 ; 隔开)
Socials (可选)
Addresses (可选)
