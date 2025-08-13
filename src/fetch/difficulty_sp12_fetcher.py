from common.utility import utility
import os
import json
import asyncio

class difficulty_sp12_data:
    # ファイルの場所
    _FILE_PATH = './dist/difficulty/sp12'
    # ファイル名
    _FILES = {
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'difficulty': 'difficulty.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://iidx-sp12.github.io/songs.json'
    }

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))

    # 難易度表取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        # 200 OKの場合
        if res.status_code == 200:
            songs = json.load(res)
            lst = []
            dct = {}
            difficulty = {
                'normal':{
                    '-1': '未定',
                },
                'hard':{
                    '-1': '未定',
                }
            }
            for song in songs:
                # IDを取得
                id = textage_data.get_song_id(song['name'])
                if id == -1:
                    self._logging.error('[sp12]:'+ song['name'])
                id_str = str(id)
                n_value = int(song['n_value'])
                h_value = int(song['h_value'])
                if n_value == 0:
                    n_value = -1
                if h_value == 0:
                    h_value = -1
                # 惑星鉄道のデータのエラーを回避
                if song['name'] == '惑星鉄道':
                    n_value = 10
                    h_value = 10
                else :
                    # ノマゲ難易度の文字の取得
                    if n_value >= 0:
                        difficulty['normal'][str(n_value)] = song['normal']
                    # ハード難易度の文字の取得
                    if h_value >= 0:
                        difficulty['hard'][str(h_value)] = song['hard']
                # データの成形
                lst.append({
                    'id': id,
                    'difficulty': song['difficulty'],
                    'n_value': n_value,
                    'h_value': h_value
                })
                if not id_str in dct:
                    dct[id_str] = {}
                dct[id_str][song['difficulty']] = {
                    'n_value': n_value,
                    'h_value': h_value
                }
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(lst, os.path.join(self._FILE_PATH, self._FILES['list'])),
                utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict'])),
                utility.save_to_file(difficulty, os.path.join(self._FILE_PATH, self._FILES['difficulty']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading difficulty_sp12.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('difficulty_sp12 was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch difficulty_sp12.')
        
