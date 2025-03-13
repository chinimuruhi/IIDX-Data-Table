from common.utility import utility
import os
import asyncio

class konami_data:
    # ファイルの場所
    _FILE_PATH = './dist/konami'
    # ファイル名
    _FILES = {
        'dev': 'dev.json',
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'difficulty': 'difficulty.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://p.eagate.573.jp/game/infinitas/2/music/index.html'
    }

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
    
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        dct = {
            'html': res.text
        }
        await asyncio.gather(
            utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict']))
        )
        