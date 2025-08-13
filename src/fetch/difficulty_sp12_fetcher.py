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

    
    _TABLE_DIFFICULTY = {
        'S+': 10,
        'S': 9,
        'A+': 8,
        'A': 7,
        'B+': 6,
        'B': 5,
        'C': 4,
        'D': 3,
        'E': 2,
        'F': 1,
        '未定': -1,
        '不明': -2
    }
    
    _SUB_DIFFICULTY = [
        [0, '地力'],
        [0.5, '個人差']
    ]

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
                'normal': {},
                'hard': {}
            }
            difficulty_rev = {
                'normal': {},
                'hard': {}
            }
            for diff_key in self._TABLE_DIFFICULTY:
                diff_value = self._TABLE_DIFFICULTY[diff_key]
                if diff_value >=0 and diff_value <= 11:
                    for diff_sub in self._SUB_DIFFICULTY:
                        diff_subvalue = diff_value - diff_sub[0]
                        diff_subkey = diff_sub[1] + diff_key
                        difficulty['normal'][str(diff_subvalue)] = diff_subkey
                        difficulty['hard'][str(diff_subvalue)] = diff_subkey
                        difficulty_rev['normal'][diff_subkey] = diff_subvalue
                        difficulty_rev['hard'][diff_subkey] = diff_subvalue
                else:
                    difficulty['normal'][str(diff_value)] = diff_key
                    difficulty['hard'][str(diff_value)] = diff_key
                    difficulty_rev['normal'][diff_key] = diff_value
                    difficulty_rev['hard'][diff_key] = diff_value

            for song in songs:
                # IDを取得
                id = textage_data.get_song_id(song['name'])
                if id == -1:
                    self._logging.error('[sp12]:'+ song['name'])
                id_str = str(id)
                normal = song['normal']
                hard = song['hard']
                if normal and normal in difficulty_rev['normal']:
                    n_value = difficulty_rev['normal'][normal]
                else:
                    n_value = -1
                if hard and hard in difficulty_rev['hard']:
                    h_value = difficulty_rev['hard'][hard]
                else:
                    h_value = -1
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
        
