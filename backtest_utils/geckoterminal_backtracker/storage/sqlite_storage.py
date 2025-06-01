"""
SQLite 存储模块
用于将数据保存到 SQLite 数据库
"""

import os
import sqlite3
import pandas as pd


class SQLiteStorage:
    """
    SQLite 存储类，用于将数据保存到 SQLite 数据库
    """
    def __init__(self, db_path='data/geckoterminal_data.db'):
        """
        初始化 SQLite 存储
        
        参数:
            db_path (str): 数据库文件路径
        """
        # 确保 db_path 是有效路径
        if not db_path:
            db_path = 'data/geckoterminal_data.db'
            
        # 如果 db_path 是目录，则在其中创建默认数据库文件
        if os.path.isdir(db_path) or not os.path.splitext(db_path)[1]:
            os.makedirs(db_path, exist_ok=True)
            self.db_path = os.path.join(db_path, 'geckoterminal_data.db')
        else:
            # 确保目录存在
            directory = os.path.dirname(db_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            self.db_path = db_path
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库，创建必要的表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建 OHLC 数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ohlc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network TEXT NOT NULL,
            pool_address TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            aggregate INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            base_token_address TEXT,
            base_token_name TEXT,
            base_token_symbol TEXT,
            quote_token_address TEXT,
            quote_token_name TEXT,
            quote_token_symbol TEXT,
            UNIQUE(network, pool_address, timeframe, aggregate, timestamp)
        )
        ''')
        
        # 创建索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ohlc_lookup 
        ON ohlc_data (network, pool_address, timeframe, aggregate, timestamp)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ohlc_timestamp 
        ON ohlc_data (timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_ohlc(self, df, network, pool_address, timeframe, aggregate):
        """
        保存 OHLC 数据到 SQLite 数据库
        
        参数:
            df (pandas.DataFrame): OHLC 数据
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期
            aggregate (int): 聚合周期
        """
        if df.empty:
            print("No data to save")
            return
            
        # 添加网络和池子信息
        df['network'] = network
        df['pool_address'] = pool_address
        df['timeframe'] = timeframe
        df['aggregate'] = aggregate
        
        # 连接数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 分批处理数据
        total_rows = len(df)
        batch_size = 100  # 每批处理的数据量
        batches_total = (total_rows - 1) // batch_size + 1
        
        for i in range(0, total_rows, batch_size):
            batch_num = i // batch_size + 1
            chunk = df.iloc[i:i+batch_size]
            
            # 使用 to_sql 的方式保存数据，但需要处理重复数据
            # 首先获取当前批次的所有时间戳
            timestamps = chunk['timestamp'].tolist()
            networks = chunk['network'].tolist()
            pool_addresses = chunk['pool_address'].tolist()
            timeframes = chunk['timeframe'].tolist()
            aggregates = chunk['aggregate'].tolist()
            
            # 构建查询条件
            placeholders = ", ".join(["(?, ?, ?, ?, ?)" for _ in range(len(timestamps))])
            
            # 查询数据库中已存在的记录
            query = f"""
            SELECT network, pool_address, timeframe, aggregate, timestamp 
            FROM ohlc_data 
            WHERE (network, pool_address, timeframe, aggregate, timestamp) IN ({placeholders})
            """
            
            # 准备参数
            params = []
            for i in range(len(timestamps)):
                params.extend([networks[i], pool_addresses[i], timeframes[i], int(aggregates[i]), int(timestamps[i])])
            
            cursor.execute(query, params)
            existing_records = cursor.fetchall()
            
            # 将现有记录转换为集合，便于快速查找
            existing_set = set()
            for record in existing_records:
                existing_set.add((record[0], record[1], record[2], record[3], record[4]))
            
            # 分离需要插入和需要更新的记录
            to_insert = pd.DataFrame(columns=chunk.columns)
            
            for idx, row in chunk.iterrows():
                key = (row['network'], row['pool_address'], row['timeframe'], int(row['aggregate']), int(row['timestamp']))
                if key not in existing_set:
                    to_insert = pd.concat([to_insert, pd.DataFrame([row])], ignore_index=True)
            
            # 插入新记录
            if not to_insert.empty:
                # 将数据类型转换为 SQLite 支持的类型
                for col in to_insert.columns:
                    if to_insert[col].dtype == 'int64':
                        to_insert[col] = to_insert[col].astype('int32')
                    elif to_insert[col].dtype == 'float64':
                        to_insert[col] = to_insert[col].astype('float32')
                    elif to_insert[col].dtype == 'bool':
                        to_insert[col] = to_insert[col].astype('int32')
                
                # 使用 to_sql 插入新记录
                to_insert.to_sql('ohlc_data', conn, if_exists='append', index=False)
            
            # 每批次提交
            conn.commit()
            print(f"Processed batch {batch_num}/{batches_total}")
        
        # 关闭连接
        conn.close()
        
        print(f"Data saved to database {self.db_path}, table ohlc_data")
    
    def load_ohlc(self, network, pool_address, timeframe, aggregate, 
                  start_timestamp=None, end_timestamp=None, file_path=None):
        """
        从 SQLite 数据库加载 OHLC 数据
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe (str): 时间周期
            aggregate (int): 聚合周期
            start_timestamp (int): 开始时间戳
            end_timestamp (int): 结束时间戳
            file_path (str, optional): 直接指定文件路径，如果提供则从CSV文件加载
            
        返回:
            pandas.DataFrame: OHLC 数据
        """
        # 如果提供了文件路径，直接从CSV加载
        if file_path and os.path.exists(file_path):
            print(f"Loading data from CSV file: {file_path}")
            df = pd.read_csv(file_path)
            
            # 转换时间戳为 datetime
            if 'timestamp' in df.columns and 'datetime' not in df.columns:
                try:
                    # First try parsing as Unix timestamp
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                except ValueError:
                    try:
                        # If that fails, try parsing as ISO format
                        df['datetime'] = pd.to_datetime(df['timestamp'])
                    except Exception as e:
                        print(f"Error parsing timestamp: {str(e)}")
                        return pd.DataFrame()
            elif 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            return df
        
        # 构建查询
        query = '''
        SELECT * FROM ohlc_data 
        WHERE network = ? AND pool_address = ? AND timeframe = ? AND aggregate = ?
        '''
        params = [network, pool_address, timeframe, aggregate]
        
        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)
            
        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)
            
        query += ' ORDER BY timestamp'
        
        # 连接数据库
        conn = sqlite3.connect(self.db_path)
        
        # 执行查询
        df = pd.read_sql_query(query, conn, params=params)
        
        # 关闭连接
        conn.close()
        
        # 确保 datetime 列是日期时间类型
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'timestamp' in df.columns:
            # 如果没有 datetime 列，但有 timestamp 列，创建一个
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        return df
    
    def get_available_networks(self):
        """
        获取可用的网络列表
        
        返回:
            list: 网络列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT network FROM ohlc_data')
        networks = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return networks
    
    def load_ohlc_data(self, network, pool_address, timeframe_str):
        """
        从 SQLite 数据库加载 OHLC 数据（load_ohlc 的别名）
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            timeframe_str (str): 时间周期字符串，格式为 'timeframe_aggregate' 或 'timeframe'
            
        返回:
            pandas.DataFrame: OHLC 数据
        """
        # 解析时间周期字符串
        if '_' in timeframe_str:
            timeframe, aggregate = timeframe_str.split('_')
            aggregate = int(aggregate)
        else:
            timeframe = timeframe_str
            aggregate = 1
            
        return self.load_ohlc(network, pool_address, timeframe, aggregate)
    
    def get_available_pools(self, network=None):
        """
        获取可用的池子列表
        
        参数:
            network (str): 网络 ID，如果为 None 则获取所有网络的池子
            
        返回:
            list: 池子列表，每项包含 network, pool_address, base_token_symbol, quote_token_symbol
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if network:
            cursor.execute('''
            SELECT DISTINCT network, pool_address, base_token_symbol, quote_token_symbol 
            FROM ohlc_data 
            WHERE network = ?
            ''', (network,))
        else:
            cursor.execute('''
            SELECT DISTINCT network, pool_address, base_token_symbol, quote_token_symbol 
            FROM ohlc_data
            ''')
            
        pools = [
            {
                'network': row[0],
                'pool_address': row[1],
                'base_token_symbol': row[2],
                'quote_token_symbol': row[3],
                'name': f"{row[2]}/{row[3]}" if row[2] and row[3] else row[1]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return pools
    
    def save_dataframe(self, df, table_name):
        """
        将 DataFrame 保存到 SQLite 数据库的指定表中
        
        参数:
            df (pandas.DataFrame): 要保存的数据库
            table_name (str): 表名
        """
        if df.empty:
            print("No data to save")
            return
            
        # 连接数据库
        conn = sqlite3.connect(self.db_path)
        
        # 将数据类型转换为 SQLite 支持的类型
        for col in df.columns:
            if df[col].dtype == 'int64':
                df[col] = df[col].astype('int32')
            elif df[col].dtype == 'float64':
                df[col] = df[col].astype('float32')
            elif df[col].dtype == 'bool':
                df[col] = df[col].astype('int32')
        
        # 使用 to_sql 保存数据
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # 关闭连接
        conn.close()
        
        print(f"Data saved to database {self.db_path}, table {table_name}")
    
    def get_available_timeframes(self, network, pool_address):
        """
        获取可用的时间周期
        
        参数:
            network (str): 网络 ID
            pool_address (str): 池子地址
            
        返回:
            list: 时间周期列表，每项包含 timeframe, aggregate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT timeframe, aggregate 
        FROM ohlc_data 
        WHERE network = ? AND pool_address = ?
        ''', (network, pool_address))
        
        timeframes = [
            {
                'timeframe': row[0],
                'aggregate': row[1],
                'name': f"{row[0]}_{row[1]}"
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return timeframes
