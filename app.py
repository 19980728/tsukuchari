import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import seaborn
from datetime import timedelta

st.set_page_config(page_title='つくチャリ利用実績',layout='wide')
seaborn.set(font='IPAexGothic')

st.subheader('「つくチャリ」利用分析')
with st.expander('つくチャリとは'):
    st.markdown('''
        #### HP → https://interstreet.jp/tsuku-chari/
        「つくチャリ」はつくば市が行っているシェアサイクルの実証実験。

        つくば市の公共交通を補完する新しい移動手段として市民への普及を進めている。

        スマートフォンの専用アプリを用いて、各地に配置されたサイクルステーションで自転車を借りるという形式。

        片道のみの利用も可能で、まちなかの観光、通勤・通学、ショッピング等さまざまな利用方法が可能。

        2022-9時点での総台数:133台
    ''')

capa = 133

#元データdf
df = pd.read_excel('./つくチャリ利用実績R3.10-R4.3.xlsx')
df = pd.DataFrame(
    data=[
        df['開始日時'].dt.strftime('%Y-%m-%d %H:%M'),
        df['返却日時'].dt.strftime('%Y-%m-%d %H:%M'),
        df['返却日時'] - df['開始日時'],
        df['利用料金'],
        df['開始ステーション名'],
        df['返却ステーション名']
    ],
    index=['開始日時','返却日時','利用時間','利用料金','開始ステーション名','返却ステーション名']
).T
df['開始日時'] = pd.to_datetime(df['開始日時'])
df['返却日時'] = pd.to_datetime(df['返却日時'])
df['利用時間'] = pd.to_datetime(df['利用時間']).dt.strftime('%H:%M')

df['利用時間（分）'] = 60 * pd.to_datetime(df['利用時間']).dt.hour + pd.to_datetime(df['利用時間']).dt.minute

for x in ['開始','返却']:
    df[f'{x}曜日'] = df[f'{x}日時'].dt.day_name()
    df[f'{x}日'] = df[f'{x}日時'].dt.date
    df[f'{x}時間帯'] = df[f'{x}日時'].dt.hour
    df[f'{x}分'] = df[f'{x}日時'].dt.minute

#期間を超えて返却されたデータを削除
for i,r in df.iterrows():
    if r['返却日'] not in df['開始日'].unique():
        df.drop(i,axis=0,inplace=True)

#本アプリ利用者によるquery
st.sidebar.caption('取り出したいデータの条件を指定')
with st.sidebar.expander('期間'):
    date_from,date_to = st.select_slider(
        '選択',
        options=df['開始日'].unique(),
        value=( df['開始日'].unique().tolist()[0] , df['開始日'].unique().tolist()[-1] )
    )
with st.sidebar.expander('開始ステーション名'):
    stations_from = st.multiselect(
        '選択',
        options=df['開始ステーション名'].unique(),
        default=df['開始ステーション名'].unique()
    )
with st.sidebar.expander('返却ステーション名'):
    stations_to = st.multiselect(
        '選択',
        options=df['返却ステーション名'].unique(),
        default=df['返却ステーション名'].unique()
    )
df = df.query('@date_from <= 開始日 <= @date_to')
df = df.query('開始ステーション名 in @stations_from')
df = df.query('返却ステーション名 in @stations_to')

#表示用データdf_display
df_display = df.loc[:,['開始日時','返却日時','利用時間','利用料金','開始ステーション名','返却ステーション名']]
st.caption('利用実績表の表示（※公式HPからダウンロード後、excel上で簡単に加工済）')
with st.expander('利用実績データ',expanded=True):
    st.dataframe(df_display)

#稼働率計算用データdf_daily,df_monthly
df_daily = pd.DataFrame(
    data=0,
    index=df['返却日'].unique(),
    columns=[i for i in range(24)]
)
for i,row in df.iterrows():
    #日跨ぎなし
    if row['開始日'] == row['返却日']:
        #時間帯跨ぎなし
        if row['開始時間帯'] == row['返却時間帯']:
            df_daily.at[row['開始日'],row['開始時間帯']] += row['利用時間（分）']
        #時間帯跨ぎあり
        else:
            h = row['開始時間帯']
            df_daily.at[row['開始日'],h] += (60 - row['開始分'])
            h += 1
            while h != row['返却時間帯']:
                df_daily.at[row['開始日'],h] += 60
                h += 1
            else:
                df_daily.at[row['開始日'],h] += row['返却分']
    #日跨ぎあり
    else:
        d,h = row['開始日'],row['開始時間帯']
        df_daily.at[d,h] += (60 - row['開始分'])
        h += 1
        while d != row['返却日']:
            while h < 24:
                df_daily.at[d,h] += 60
                h += 1
            else:
                h = 0
                d += timedelta(days=1)
        else:
            while h != row['返却時間帯']:
                df_daily.at[d,h] += 60
                h += 1
            else:
                df_daily.at[d,h] += row['返却分']

for i in range(24):
    df_daily[i] = 100 * df_daily[i] / (60 * capa)
df_daily['all'] = df_daily.mean(axis=1)
df_daily['date'] = pd.to_datetime(df_daily.index)
df_monthly = df_daily.resample('M',on='date').mean().reset_index()

df_daily['day_name'] = df_daily['date'].dt.day_name()
df_daily.drop(columns='date',inplace=True)

df_monthly['month'] = df_monthly['date'].dt.strftime('%Y-%m')
df_monthly.drop(columns='date',inplace=True)
df_monthly = df_monthly.set_index('month')

#日、時間帯ごとの入出庫カウントデータdf_in,df_outと差し引き入庫データdf_remain
df_in = pd.DataFrame(
    data=0,
    index=df['返却日'].unique(),
    columns=[i for i in range(24)]
)
df_out = pd.DataFrame(
    data=0,
    index=df['返却日'].unique(),
    columns=[i for i in range(24)]
)
for i,row in df.iterrows():
    df_in.at[row['開始日'],row['開始時間帯']] += 1
    df_out.at[row['返却日'],row['返却時間帯']] += 1

df_remain = df_in - df_out

#滞在時間分析用データdf_stay
df_stay = df.copy()
for i in range(24):
    df_stay[i] = 0
# df_stay['count'] = 0
df_stay['group'] = 0
for i,row in df.iterrows():
    df_stay.at[i,row['開始時間帯']] += row['利用時間（分）']
    # df_stay.at[i,'count'] += 1
    df_stay.at[i,'group'] += int( row['利用時間（分）'] / 10 + 1 ) * 10 #n分以内ののnを計算

Labels = df_stay['group'].unique()
Labels.sort()
Count = []
for i in range(len(Labels)):
    Count.append( len(df_stay.query('group == @Labels[@i]')) )
Labels = [f'〜{l}分' for l in Labels]
df_stay_group = pd.DataFrame(
    data=Count,
    index=Labels,
    columns=['件数']
)

# df_stay = df_stay.loc[:,['開始日時']+[i for i in range(24)]]
# df_stay = df_stay.resample('D',on='開始日時').sum()
# df_stay = df_stay / df_in
# df_stay = df_stay.fillna(0)
df_stay = df_stay.loc[:,['開始日']+[i for i in range(24)]].set_index('開始日')
df_ios = pd.DataFrame(
    data=[df_in.sum(),df_out.sum(),df_stay.sum()],
    index=['in','out','stay']
)
df_ios.loc['stay'] = df_ios.loc['stay'] / df_ios.loc['in']
df_ios.loc['in'] = df_in.mean()
df_ios.loc['out'] = df_out.mean()
df_ios.loc['in - out'] = df_ios.loc['in'] - df_ios.loc['out']


### 各dataframeの説明
# df : 大元のデータ。取り込んだexelデータを拡張したもの。sidebarからqueryおり、以下のdataframeはquery後のdfを用いて作成している。
# df_display : dfを表示用に削ったもの。残した項目は['開始日時','返却日時','利用時間','利用料金','開始ステーション名','返却ステーション名']
# df_daily : 時間帯ごとの稼働率を日別に集計したもの。all列は全時間帯の平均。　→時間帯ごとの稼働率グラフ描画
# df_daily2 : df_dailyを曜日でqueryしたもの。　→時間帯ごとの稼働率グラフ描画
# df_monthly : 時間帯ごとの稼働率を月別に集計したもの。all列は全時間帯の平均。　→月ごとの稼働率推移グラフ描画
# df_in,df_out : 日、時間帯ごとに利用開始件数、返却件数をそれぞれ集計したもの。
# df_stay : 日、時間帯ごとに利用開始した利用者の平均利用時間を集計したもの。
# df_stay_group : 各利用者ごとの利用時間をその長さにより分類し、合計して集計したもの。　→利用時間分布円グラフ描画
# df_ios : df_in,df_out,df_stayの3つについて時間帯ごとに全期間の平均をとって束ねたもの。
# df_remain : df_in - df_out により得られた差し引き入庫台数の表。
###


st.caption('利用分析グラフの表示')

#月ごとの稼働率推移グラフ描画
with st.expander('月ごとの稼働率推移グラフ'):
    fig1,ax = plt.subplots(figsize=(7,3))
    ax.plot(df_monthly.index,df_monthly['all'])
    ax.set_title('月ごとの稼働率推移')
    ax.set_ylabel('%',rotation='horizontal')
    st.pyplot(fig1)

#時間帯ごとの稼働率グラフ描画
with st.expander('時間帯ごとの稼働率グラフ'):
    day_name = st.select_slider(
        '曜日を選択',
        options=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    )
    df_daily2 = df_daily.query('day_name == @day_name') #曜日を絞ったdf_daily
    occu_all = df_daily.drop(columns=['all','day_name']).mean(axis=0) #全日の稼働率
    occu_selected = df_daily2.drop(columns=['all','day_name']).mean(axis=0) #queryした曜日の稼働率

    fig2,ax = plt.subplots(figsize=(7,3))
    ax.plot([i for i in range(24)],occu_all,label='全日')
    ax.plot([i for i in range(24)],occu_selected,label=day_name)
    ax.legend()
    ax.set_title('時間帯ごとの稼働率')
    ax.set_ylabel('％',rotation='horizontal')
    ax.set_xticks([i for i in range(24)])
    st.pyplot(fig2)

#時間帯ごとの利用分析グラフ描画
with st.expander('時間帯ごとの利用分析グラフ'):
    fig3,ax1 = plt.subplots(figsize=(7,3))
    ax2 = ax1.twinx()
    ax1.plot(df_ios.columns,df_ios.loc['in'],color='blue',label='平均入庫台数')
    ax1.plot(df_ios.columns,df_ios.loc['out'],color='aquamarine',label='平均出庫台数')
    # ax1.plot(df_ios.columns,df_ios.loc['in - out'],color='green',label='平均差し引き入庫台数')
    ax2.bar(df_ios.columns,df_ios.loc['stay'],tick_label=df_ios.columns,color='red',alpha=0.4)
    ax1.legend()
    ax1.set_title('時間帯ごとの利用分析')
    ax1.set_ylabel('平均入出庫台数（台）')
    ax2.set_ylabel('平均利用時間（分）')
    ax2.spines['left'].set_color('blue')
    ax2.spines['right'].set_color('red')
    ax1.tick_params(axis='y', colors='blue')
    ax2.tick_params(axis='y', colors='red')
    st.pyplot(fig3)

#利用時間分布円グラフ描画
with st.expander('利用時間分布円グラフ'):
    fig4,ax = plt.subplots()
    ax.pie(x=df_stay_group['件数'],  #データ
            labels=Labels,  #ラベル
            radius=0.8,  #円の半径
            counterclock=False,  #時計回り
            startangle=90, #開始角度90度
            textprops={'size':'xx-small'})
    # ax.legend(loc=[0,0],fontsize='xx-small')
    st.pyplot(fig4)

#入庫・出庫・差し引き入庫台数データ表
st.caption('より詳細なデータの表示')
def resample(D):
    D2 = D.reset_index()
    D2['index'] = pd.to_datetime(D2['index'])
    D2 = D2.resample('M',on='index').mean().reset_index()
    D2['index'] = D2['index'].dt.strftime('%Y-%m')
    D2 = D2.set_index('index')
    return D2
if st.checkbox('月次平均で表示'):
    df_in = resample(df_in)
    df_out = resample(df_out)
    df_remain = resample(df_remain)
with st.expander('入庫台数データ表'):
    st.dataframe(df_in)
with st.expander('出庫台数データ表'):
    st.dataframe(df_out)
with st.expander('差し引き入庫台数データ表'):
    st.dataframe(df_remain)