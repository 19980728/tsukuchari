import streamlit as st
import mymodule

# 基礎部分
st.set_page_config('tsukuchari-report',layout='wide')
st.title('「つくチャリ」レポート')
with st.expander('「つくチャリ」とは'):
    st.markdown('''
        公式HP → https://interstreet.jp/tsuku-chari/

        「つくチャリ」はつくば市が行っているシェアサイクルの実証実験。

        つくば市の公共交通を補完する新しい移動手段として市民への普及を進めている。

        スマートフォンの専用アプリを用いて、各地に配置されたサイクルステーションで自転車を借りるという形式。

        片道のみの利用も可能で、まちなかの観光、通勤・通学、ショッピング等さまざまな利用方法が可能。

        *2022-9時点での総台数:133台
    ''')
# with st.expander('「つくチャリ」ステーション情報'):
#     st.write('編集中')
with st.expander('本レポートの説明'):
    st.markdown('''
        本レポートは「つくチャリ」公式HPから入手可能な利用実績データをもとに、
        「つくチャリ」が現在どのように利用されているのか分析したものになります。

        下の各項目をクリックして分析結果をご覧ください。

        「データを制限」の項目から期間やステーション名を選択することで必要なデータだけを抜き出して分析することが可能です。

        分析内容の説明:

        ・まずは最も利用状況について分かりやすい指標として、稼働率を示してあります。

        （ ※稼働率 = (実際に利用された時間) / (利用可能な時間の合計) ）

        ・次により詳細な利用情報として、時間帯ごとに利用開始された台数と返却された台数を示しています。

        これを見ることで、どの時間帯に使い始め、どの時間帯に利用終了する人が多いのかを知ることが出来ます。

        ・最後に利用時間の分布をグラフで示してあります。何分利用する人が多いのかがここから分かります。
    ''')

# アップロードしたデータからdataframeを作成
df = mymodule.df
with st.expander('データを制限'):
    date_from,date_to = st.select_slider(
        label='開始日時によりデータを制限',
        options=df['開始日'].unique().tolist(),
        value=(df['開始日'].unique().tolist()[0],df['開始日'].unique().tolist()[-1])
        )
    stations_from = st.multiselect(
        '開始ステーションによりデータを制限',
        options=df['開始ステーション名'].unique(),
        default=df['開始ステーション名'].unique()
    )
    stations_to = st.multiselect(
        '返却ステーションによりデータを制限',
        options=df['返却ステーション名'].unique(),
        default=df['返却ステーション名'].unique()
    )
df = df.query('@date_from <= 開始日 <= @date_to')
df = df.query('開始ステーション名 in @stations_from')
df = df.query('返却ステーション名 in @stations_to')
df,df_occu,df_in,df_out,df_remain,df_stay,df_stay_group,fig_d,fig_h,fig_io,fig_s,fig_is = mymodule.analyze(df)

# データ加工結果の表示
with st.expander('利用実績データ',expanded=True):
    st.dataframe(df.loc[:,['開始日時','開始曜日','返却日時','利用時間','開始ステーション名','返却ステーション名']])
st.caption('稼働率分析')
with st.expander('稼働率表'):
    st.dataframe(df_occu)
with st.expander('日ごとの稼働率グラフ'):
    st.pyplot(fig_d)
with st.expander('時間帯ごとの稼働率グラフ'):
    st.pyplot(fig_h)
st.caption('利用開始・返却台数分析')
with st.expander('利用開始・返却表'):
    option = st.radio('SELECT:',options=['時間帯ごとの利用開始台数表','時間帯ごとの返却台数表','差引利用開始台数表'])
    if option == '時間帯ごとの利用開始台数表':
        st.dataframe(df_in)
    elif option == '時間帯ごとの返却台数表':
        st.dataframe(df_out)
    else:
        st.dataframe(df_remain)
with st.expander('利用開始・返却台数グラフ'):
    st.pyplot(fig_io)
st.caption('利用時間分析')
with st.expander('利用時間分布グラフ'):
    st.pyplot(fig_s)
with st.expander('利用開始時間帯ごとの平均利用時間'):
    st.dataframe(df_stay)
    st.pyplot(fig_is)