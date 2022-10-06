import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import seaborn
seaborn.set(font='IPAexGothic')
from datetime import timedelta

capa = 133
file_path = 'data_tsukuchariR3.10-R4.6.xlsx'

# make df
df = pd.read_excel(file_path)
df = pd.DataFrame(
    data = [df['開始日時'].dt.strftime('%Y-%m-%d %H:%M'),
            df['返却日時'].dt.strftime('%Y-%m-%d %H:%M'),
            df['返却日時'] - df['開始日時'],
            df['開始ステーション名'],
            df['返却ステーション名']],
    index = ['開始日時','返却日時','利用時間','開始ステーション名','返却ステーション名'] 
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


def analyze(df):
    # make df_occu - 稼働率表
    df_occu = pd.DataFrame(
        data=0,
        index=df['返却日'].unique(),
        columns=[i for i in range(24)]
    )
    for i,row in df.iterrows():
        #日跨ぎなし
        if row['開始日'] == row['返却日']:
            #時間帯跨ぎなし
            if row['開始時間帯'] == row['返却時間帯']:
                df_occu.at[row['開始日'],row['開始時間帯']] += row['返却分'] - row['開始分']
            #時間帯跨ぎあり
            else:
                h = row['開始時間帯']
                df_occu.at[row['開始日'],h] += (60 - row['開始分'])
                h += 1
                while h != row['返却時間帯']:
                    df_occu.at[row['開始日'],h] += 60
                    h += 1
                else:
                    df_occu.at[row['開始日'],h] += row['返却分']
        #日跨ぎあり
        else:
            d,h = row['開始日'],row['開始時間帯']
            df_occu.at[d,h] += (60 - row['開始分'])
            h += 1
            while d != row['返却日']:
                while h < 24:
                    df_occu.at[d,h] += 60
                    h += 1
                else:
                    h = 0
                    d += timedelta(days=1)
            else:
                while h != row['返却時間帯']:
                    df_occu.at[d,h] += 60
                    h += 1
                else:
                    df_occu.at[d,h] += row['返却分']

    for i in range(24):
        df_occu[i] = 100 * df_occu[i] / (60 * capa)
    df_occu.sort_index(inplace=True)

    # mak df_in, df_out, df_remain - 開始・返却台数表
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

    # make df_stay - 開始時間ごとの利用時間平均表
    df_stay = pd.DataFrame(
        data = 0,
        index = ['件数','平均利用時間'],
        columns = [i for i in range(24)]
    )
    for i,row in df.iterrows():
        df_stay.at['件数',row['開始時間帯']] += 1
        df_stay.at['平均利用時間',row['開始時間帯']] += row['利用時間（分）']
    df_stay.loc['平均利用時間'] = df_stay.loc['平均利用時間'] / df_stay.loc['件数']

    # make df_stay_group - 利用時間分布表
    labels = []
    rate = []
    for i in range(6):
        labels.append(f'〜{10*(i+1)}分')
        rate.append( len( df[ (df['利用時間（分）'] >= 10*i) & (df['利用時間（分）'] < 10*(i+1)) ] ) )
    for i in range(1,6):
        labels.append(f'〜{i+1}時間')
        rate.append( len( df[ (df['利用時間（分）'] >= 60*i) & (df['利用時間（分）'] < 60*(i+1)) ] ) )
    labels.append('〜12時間')
    rate.append( len( df[ (df['利用時間（分）'] >= 60*6) & (df['利用時間（分）'] < 60*12) ] ) )
    labels.append('〜24時間')
    rate.append( len( df[ (df['利用時間（分）'] >= 60*12) & (df['利用時間（分）'] < 60*24) ] ) )
    labels.append('24時間〜')
    rate.append( len( df[ df['利用時間（分）'] >= 60*24 ] ) )
    df_stay_group = pd.DataFrame(
        data=[100*r/len(df) for r in rate],
        index=labels,
        columns=['割合（％）']
        ).T

    # 稼働率関連のグラフ
    fig_d,ax_d = plt.subplots(figsize=(7,3))
    ax_d.set_title('日ごとの稼働率')
    ax_d.plot(df_occu.mean(axis=1),color='blue')
    ax_d.set_ylabel('%',rotation='horizontal')
    plt.xticks(rotation=45)

    fig_h,ax_h = plt.subplots(figsize=(7,3))
    ax_h.set_title('時間帯ごとの稼働率')
    ax_h.plot(df_occu.mean(axis=0),color='red')
    ax_h.set_ylabel('%',rotation='horizontal')
    ax_h.set_xticks([i for i in range(24)])

    # 開始・返却台数のグラフ
    fig_io,ax_io = plt.subplots(figsize=(7,3))
    ax_io.set_title('時間帯ごとの開始・返却台数')
    ax_io.plot(df_in.mean(),color='blue',label='平均利用開始台数')
    ax_io.plot(df_out.mean(),color='green',label='平均返却台数')
    ax_io.bar(x=df_remain.columns,height=df_remain.mean(),color='blue',label='差し引き利用開始台数')
    ax_io.set_xticks([i for i in range(24)])
    ax_io.legend()

    # 利用時間分布のグラフ
    fig_s,ax_s = plt.subplots()
    ax_s.set_title('利用時間分布')
    ax_s.pie(
        x=rate,
        labels=labels,
        counterclock=False,
        startangle=90,
        textprops={'size':'xx-small'},
        labeldistance=None
        )
    ax_s.legend()

    # 利用開始時間と利用時間の関係グラフ
    fig_is,ax_is = plt.subplots(figsize=(7,3))
    ax_is_2 = ax_is.twinx()
    ax_is.set_title('利用開始時間と利用時間の関係')
    ax_is.plot(df_in.mean(),color='blue',label='平均利用開始台数')
    ax_is_2.bar(x=df_stay.columns,height=df_stay.loc['平均利用時間'],color='red',label='平均利用時間',alpha=0.4)
    ax_is.set_xticks([i for i in range(24)])
    ax_is.set_ylabel('平均利用開始台数（台）')
    ax_is_2.set_ylabel('平均利用時間（分）')
    ax_is_2.spines['left'].set_color('blue')
    ax_is_2.spines['right'].set_color('red')
    ax_is.tick_params(axis='y', colors='blue')
    ax_is_2.tick_params(axis='y', colors='red')

    return df, df_occu, df_in, df_out, df_remain, df_stay, df_stay_group, fig_d, fig_h, fig_io, fig_s, fig_is