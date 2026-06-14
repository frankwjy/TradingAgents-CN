"""
Streamlit WebUI 弃用通知组件
提醒用户迁移到新的 Vue.js 前端
"""

import streamlit as st
import os


def render_deprecation_notice():
    """
    渲染弃用通知横幅
    提醒用户 Streamlit WebUI 已弃用，建议使用新的 Vue.js 前端
    """
    # 从环境变量读取新前端地址，默认为 localhost:3000
    vue_frontend_url = os.getenv("VUE_FRONTEND_URL", "http://localhost:3000")

    # 检查是否已经关闭过通知
    if st.session_state.get("deprecation_notice_dismissed", False):
        return

    # 弃用通知样式
    st.markdown("""
    <style>
    .deprecation-banner {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(238, 90, 36, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    .deprecation-banner h3 {
        color: white;
        margin: 0 0 0.5rem 0;
        font-size: 1.2rem;
        font-weight: 600;
    }

    .deprecation-banner p {
        color: rgba(255, 255, 255, 0.95);
        margin: 0.3rem 0;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    .deprecation-banner a {
        color: #fff;
        text-decoration: underline;
        font-weight: 600;
    }

    .deprecation-banner a:hover {
        color: #ffd700;
    }

    .deprecation-features {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.8rem 0;
    }

    .deprecation-feature-tag {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.8rem;
        color: white;
    }
    </style>

    <div class="deprecation-banner">
        <h3>⚠️ Streamlit WebUI 已弃用</h3>
        <p>
            当前界面将在未来版本中移除。请迁移到功能更完善的 <a href="{url}" target="_blank">Vue.js 前端</a>。
        </p>
        <p>
            <strong>新前端优势：</strong>
        </p>
        <div class="deprecation-features">
            <span class="deprecation-feature-tag">批量分析</span>
            <span class="deprecation-feature-tag">股票筛选</span>
            <span class="deprecation-feature-tag">自选股</span>
            <span class="deprecation-feature-tag">模拟交易</span>
            <span class="deprecation-feature-tag">学习中心</span>
            <span class="deprecation-feature-tag">深色主题</span>
            <span class="deprecation-feature-tag">响应式设计</span>
            <span class="deprecation-feature-tag">实时通知</span>
        </div>
        <p style="font-size: 0.85rem; opacity: 0.9; margin-top: 0.5rem;">
            访问地址：<a href="{url}" target="_blank">{url}</a>
        </p>
    </div>
    """.format(url=vue_frontend_url), unsafe_allow_html=True)

    # 添加关闭按钮
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("✕ 关闭通知", key="dismiss_deprecation"):
            st.session_state.deprecation_notice_dismissed = True
            st.rerun()


def render_migration_guide():
    """
    渲染迁移指南（可选，在侧边栏或设置页面中显示）
    """
    vue_frontend_url = os.getenv("VUE_FRONTEND_URL", "http://localhost:3000")

    with st.expander("📖 迁移到新前端指南", expanded=False):
        st.markdown(f"""
        ### 迁移步骤

        1. **启动新前端**
           ```bash
           # 启动后端 API 服务
           python scripts/startup/start_api.py

           # 启动前端开发服务器
           python scripts/startup/start_frontend.py
           ```

        2. **访问新前端**
           - 前端地址：[{vue_frontend_url}]({vue_frontend_url})
           - API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

        3. **功能对照**

        | Streamlit 功能 | Vue.js 对应页面 |
        |----------------|-----------------|
        | 📊 股票分析 | 分析 → 单股分析 |
        | ⚙️ 配置管理 | 设置 → 配置管理 |
        | 💾 缓存管理 | 设置 → 缓存管理 |
        | 💰 Token统计 | 报表 → Token统计 |
        | 📋 操作日志 | 系统 → 操作日志 |
        | 📈 分析结果 | 分析 → 分析历史 |
        | 🔧 系统状态 | 系统 → 多源同步 |

        4. **Docker 部署（推荐）**
           ```bash
           docker-compose up -d
           ```
           - 前端：http://localhost:80 (或配置的 NGINX_PORT)
           - 后端：http://localhost:8000
        """)
