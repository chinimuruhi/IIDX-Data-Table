import ssl
import aiohttp
import io
import json
import gzip
from datetime import datetime, timezone, timedelta

class utility:
    GMT = timezone(timedelta(hours=0))
    _logging = None

    # UNIX基準時間の取得（If-Modified-Sinceの形式）
    @classmethod
    def get_unix_begin_time(cls):
        dt = datetime(1970, 1, 1, 0, 0, 0, 0, cls.GMT)
        return cls.datetime_to_string(dt)

    @classmethod
    def get_now(cls):
        dt = datetime.now(cls.GMT)
        return cls.datetime_to_string(dt)

    @classmethod
    def datetime_to_string(cls, dt):
        return datetime.strftime(dt, '%a, %d %b %Y %I:%M:%S GMT')

    @classmethod
    def init_last_modified(cls, file_path):
        try:
            with open(file_path, mode='r', encoding='utf_8') as f:
                last_modified = f.read()
                header = {
                    'If-Modified-Since': last_modified
                } 
        except:
            with open(file_path, mode= "w", encoding='utf_8') as f:
                f.write(cls.get_unix_begin_time())
                header = {
                    'If-Modified-Since': cls.get_unix_begin_time()
                } 
        return header

    @classmethod
    def update_last_modified(self, file_path):
        with open(file_path, mode= "w", encoding='utf_8') as f:
            now = utility.get_now()
            f.write(now)

    @classmethod
    async def load_from_file(cls, file_path):
        try:
            with open(file_path, mode='r', encoding='utf_8') as f:
                return json.loads(f.read())
        except:
            if cls._logging:
                cls._logging.error('Failed to load JSON from file:' + file_path)
            return {}

    @classmethod    
    async def save_to_file(cls, data, file_path):
        try:
            with open(file_path, mode='w', encoding='utf_8') as f:
                f.write(json.dumps(data, ensure_ascii=False, indent='\t', sort_keys=True, separators=(',', ': ')))
        except Exception as e:
            if cls._logging:
                cls._logging.error('Failed to save file:' + file_path)
            else:
                raise e

    @classmethod
    async def save_to_file_gz(cls, data, file_path):
        try:
            with open(file_path, mode='wb') as f:
                text = json.dumps(data, ensure_ascii=False, indent='\t', separators=(',', ': '))
                f.write(gzip.compress(bytes(text, 'utf_8')))
        except Exception as e:
            if cls._logging:
                cls._logging.error('Failed to save file:' + file_path)
            else:
                raise e
    
    @classmethod
    def load_from_gz(cls, bytes):
        try:
            return json.loads(gzip.decompress(bytes))
        except Exception as e:
            if cls._logging:
                cls._logging.error('Failed to load json from bytes.')
                return {}
            else:
                raise e

    # 修正: SSL/TLSバージョンを指定して非同期リクエストを行う
    @classmethod
    async def requests_get(cls, url, headers):
        headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        timeout = aiohttp.ClientTimeout(total=20)
        
        # SSL contextを作成してTLSv1.2を指定
        ssl_context = ssl.create_default_context()
        ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # TLS 1.0 と 1.1 を無効化

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, ssl=ssl_context) as response:
                body = await response.read()
                # 擬似的な "urllib response" のように扱うためのラップ
                fake_response = io.BytesIO(body)
                fake_response.headers = response.headers
                fake_response.status_code = response.status
                return fake_response

    @classmethod
    def set_logging(cls, logging):
        cls._logging = logging
