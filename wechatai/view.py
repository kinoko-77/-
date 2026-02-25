import streamlit as st
import pymysql
import pandas as pd
import time

st.set_page_config(page_title="储能内参 AI 版", layout="wide")
st.title("⚡ 储能行业公众号 AI 自动简报")

# 数据库配置
DB_CONFIG = {
    'host': 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'user': '4UQMmu8pBXHpYPX.root',
    'password': 'ErrvTvIZ1l1WdQ90',
    'database': 'test',
    'charset': 'utf8mb4',
    'ssl': {'ssl': True},
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30
}


# 带重试的数据库连接
def get_connection(max_retries=3):
    for i in range(max_retries):
        try:
            conn = pymysql.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(1)
                continue
            raise e


# 获取数据（带缓存）
@st.cache_data(ttl=60)
def get_data():
    try:
        conn = get_connection()
        # 明确指定列名，确保 id 是整数
        df = pd.read_sql("""
                         SELECT id,
                                category,
                                title,
                                summary,
                                publish_date,
                                link
                         FROM articles
                         ORDER BY publish_date DESC
                         """, conn)
        conn.close()
        # 确保 id 是整数类型
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()


# 更新分类
def update_category(article_id, new_category):
    try:
        # 确保 article_id 是整数
        article_id = int(float(article_id))
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "UPDATE articles SET category = %s WHERE id = %s"
            cursor.execute(sql, (new_category, article_id))
        conn.commit()
        conn.close()
        # 清除缓存，强制刷新数据
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"更新失败: {e}")
        return False


# 分类选项
CATEGORIES = ["技术研发与突破", "政策法规与市场交易", "工程项目与并网实践", "企业动向与产业经济", "基础知识与科普解读",
              "安全事件与事故处理", "其他"]

df = get_data()

# 空数据保护
if df.empty:
    st.warning("数据库中没有数据，请先添加文章数据")
    st.stop()

if 'category' not in df.columns:
    st.error(f"数据表结构不正确，缺少 category 列。当前列: {list(df.columns)}")
    st.stop()

# 调试信息（看看 id 列的实际值）
# st.write("调试 - ID列类型:", df['id'].dtype)
# st.write("调试 - ID列前5行:", df['id'].head())

# 侧边栏筛选
st.sidebar.header("筛选选项")
selected_cat = st.sidebar.multiselect("选择分类", options=df['category'].unique(), default=df['category'].unique())

# 手动修改开关
enable_edit = st.sidebar.checkbox("启用手动修改分类")

# 页面展示
filtered_df = df[df['category'].isin(selected_cat)]

# 显示统计信息
st.sidebar.markdown("---")
st.sidebar.write(f"**总计文章数:** {len(df)}")
st.sidebar.write(f"**筛选后文章数:** {len(filtered_df)}")

# 文章展示区域
for i, row in filtered_df.iterrows():
    with st.container():
        st.markdown(f"### {row['title']}")
        st.caption(f"📅 {row['publish_date']} | 🏷️ {row['category']}")
        st.success(f"**AI 摘要：** {row['summary']}")
        st.markdown(f"[🔗 点击阅读原文]({row['link']})")

        if enable_edit:
            st.markdown("---")
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                new_category = st.selectbox(
                    "修改分类:",
                    options=CATEGORIES,
                    index=CATEGORIES.index(row['category']) if row['category'] in CATEGORIES else 0,
                    key=f"select_{int(row['id'])}"
                )

            with col2:
                # 确保 button 的 key 也是整数
                if st.button("更新", key=f"update_{int(row['id'])}"):
                    if new_category != row['category']:
                        if update_category(row['id'], new_category):
                            st.success("分类更新成功！")
                            st.rerun()
                        else:
                            st.error("更新失败！")
                    else:
                        st.info("分类未改变")

            with col3:
                st.caption(f"ID: {int(row['id'])}")

        st.divider()
