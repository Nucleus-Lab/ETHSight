"""
����ͻ���ź�

����:
����һ��ָ�꣬���۸�ͻ��20�վ����ҳɽ�������50%ʱ���������ź�

����ʱ��: 2025-05-17 19:27:00
"""

import pandas as pd
import numpy as np

import pandas as pd
import numpy as np

def breakout_ma20_volume_signal(df):
    """
    ����۸�ͻ��20�վ����ҳɽ�������50%�������ź�ָ��

    ָ��˵��:
        �����̼��ϴ�20�ռ��ƶ�ƽ���ߣ�MA20�����ҵ��ճɽ�����ǰһ����������50%ʱ�����������źţ�1��������Ϊ0��
        ��ָ�����ڲ�׽�۸�ǿ��ͻ�Ʋ���������Ľ��׻��ᡣ

    ����:
        df (pandas.DataFrame): ���� OHLC �ͳɽ�������Ϣ�� DataFrame�������������:
            ['timestamp','open','high','low','close','volume','datetime',
             'base_token_address','base_token_name','base_token_symbol',
             'quote_token_address','quote_token_name','quote_token_symbol']

    ����:
        pandas.DataFrame: ��ԭʼ DataFrame ���������� 'breakout_ma20_vol_signal' �У���ʾ�����źţ�1Ϊ�źţ�0Ϊ���źţ�
    """
    df = df.copy()
    # ����20�ռ��ƶ�ƽ����
    df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
    # ����ɽ���ǰһ��
    df['volume_prev'] = df['volume'].shift(1)
    # �������̼�ǰһ��
    df['close_prev'] = df['close'].shift(1)
    # ����MA20ǰһ��
    df['ma20_prev'] = df['ma20'].shift(1)

    # ����1: ���̼۴�������ͻ��MA20
    breakout = (df['close_prev'] <= df['ma20_prev']) & (df['close'] > df['ma20'])
    # ����2: �ɽ�����ǰһ����������50%
    vol_increase = (df['volume'] >= 1.5 * df['volume_prev'])

    # �ۺ��ź�
    df['breakout_ma20_vol_signal'] = np.where(breakout & vol_increase, 1, 0)

    # ������ʱ��
    df.drop(['ma20', 'volume_prev', 'close_prev', 'ma20_prev'], axis=1, inplace=True)

    return df
