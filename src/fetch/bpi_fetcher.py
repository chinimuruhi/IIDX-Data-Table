from common.utility import utility
import os
import asyncio
import math
import json

class bpi_data:
    # ファイルの場所
    _FILE_PATH = './dist/bpi/20250915'
    # ファイル名
    _FILES = {
        'sp_list':'sp_list.json',
        'sp_dict':'sp_dict.json',
        'dp_list': 'dp_list.json',
        'dp_dict': 'dp_dict.json',
        'last_modified': 'last_modified.txt',
        'version': 'version.json'
    }
    # データ取得先
    _URLS = {
        'version': 'https://yomogi.poyashi.me/latest',
        'songs':'https://yomogi.poyashi.me/20250915'
    }
    _DIFFICULTY_MAP = {
        '1': ('SP', 'B'),
        '2': ('SP', 'N'),
        '3': ('SP', 'H'),
        '4': ('SP', 'A'),
        '7': ('DP', 'N'),
        '8': ('DP', 'H'),
        '9': ('DP', 'A'),
        '10': ('SP', 'L'),
        '11': ('DP', 'L')
    }
    _DEFAULT_COEF = 1.175
    _SCORE_RATE = {
        'AAA': 8.0/9.0,
        'MAX_MINUS': 17.0/18.0
    }
    _ERROR_DATA = (
    )

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))

    # 難易度表取得
    async def update(self, textage_data):
        # バージョンが最新の場合はスキップ
        if await self._is_latest():
            self._logging.info('bpi was not modified.')
            return
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        # 200 OKの場合
        if res.status_code == 200:
            res_json = json.load(res)
            songs = res_json['body']
            version = {
                'version': res_json['version']
            }
            sp_list = []
            sp_dict = {}
            dp_list = []
            dp_dict = {}
            for song in songs:
                # IDを取得
                id = textage_data.get_song_id(song['title'])
                if id == -1:
                    self._logging.error('[bpi]:'+ song['title'])
                id_str = str(id)
                # 難易度の変換
                mode, difficulty = self._DIFFICULTY_MAP[song['difficulty']]
                level = int(song['difficultyLevel'])
                wr = int(song['wr'])
                avg = int(song['avg'])
                notes = int(song['notes'])
                bpm = song['bpm']
                if 'coef' in song:
                    coef = float(song['coef'])
                else:
                    coef = -1
                # 不正データの除外
                is_error = False
                for e in self._ERROR_DATA:
                    if song['title'] == e[0] and song['difficulty'] == e[1]:
                        is_error = True
                        break
                if is_error:
                    self._logging.error('BPI Load Skip(1): ' + song['title'] + '[' + song['difficulty'] + ']')
                    continue
                # BPIの計算
                aaa_bpi = self._calculate_bpi(wr, avg, notes, 'AAA', coef)
                max_minus_bpi = self._calculate_bpi(wr, avg, notes, 'MAX_MINUS', coef)
                if aaa_bpi is None or max_minus_bpi is None:
                    self._logging.error('BPI Load Skip(2): ' + song['title'] + '[' + song['difficulty'] + ']')
                    continue
                # データの成形
                elm_list = {
                    'id': id,
                    'difficulty': difficulty,
                    'level': level,
                    'wr': wr,
                    'avg': avg,
                    'notes': notes,
                    'bpm': bpm,
                    'coef': coef,
                    'aaa_bpi': aaa_bpi,
                    'max_minus_bpi': max_minus_bpi
                }
                elm_dict = {
                    'level': level,
                    'wr': wr,
                    'avg': avg,
                    'notes': notes,
                    'bpm': bpm,
                    'coef': coef,
                    'aaa_bpi': aaa_bpi,
                    'max_minus_bpi': max_minus_bpi
                }
                if mode == 'SP': 
                    sp_list.append(elm_list)
                    if not id_str in sp_dict:
                        sp_dict[id_str] = {}
                    sp_dict[id_str][difficulty] = elm_dict
                else:
                    dp_list.append(elm_list)
                    if not id_str in dp_dict:
                        dp_dict[id_str] = {}
                    dp_dict[id_str][difficulty] = elm_dict
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(sp_list, os.path.join(self._FILE_PATH, self._FILES['sp_list'])),
                utility.save_to_file(sp_dict, os.path.join(self._FILE_PATH, self._FILES['sp_dict'])),
                utility.save_to_file(dp_list, os.path.join(self._FILE_PATH, self._FILES['dp_list'])),
                utility.save_to_file(dp_dict, os.path.join(self._FILE_PATH, self._FILES['dp_dict'])),
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            await utility.save_to_file(version, os.path.join(self._FILE_PATH, self._FILES['version']))
            self._logging.info('Success in loading bpi.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('bpi was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch bpi.')
    
    # 難易度表取得
    async def _is_latest(self):
        results = await asyncio.gather(
            utility.load_from_file(os.path.join(self._FILE_PATH, self._FILES['version'])),
            utility.requests_get(self._URLS['version'], self._lastmodified_header)
        )
        version = results[0]
        res = results[1]
        if not version:
            version = {
                'version':0
            }
        # 200 OKの場合
        if res.status_code == 200:
            latest = int(json.load(res)['version'])
            self._version = {
                'version':latest
            }
            return version['version'] >= latest
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._version = version
            return True
        else:
            # その他の場合
            self._logging.error('Failed to fetch bpi')
            self._version = version
            return False
        
    # BPIの計算
    # 参考：https://github.com/BPIManager/BPIManager-Core/blob/master/src/components/bpi/index.tsx
    def _pgf(self, num, max_score):
        if num == max_score:
            return max_score * 0.8
        else:
            return 1.0 + (float(num) / float(max_score) - 0.5) / (1.0 - float(num) / float(max_score))
        
    def _calculate_bpi(self, wr, avg, notes, score_rate, coef):
        try:
            max_score = notes * 2
            if coef != -1:
                powCoef = coef
            else:
                powCoef = self._DEFAULT_COEF
            ex = math.ceil(max_score * self._SCORE_RATE[score_rate])
            _s = self._pgf(ex, max_score)
            _k = self._pgf(avg, max_score)
            _z = self._pgf(wr, max_score)
            _s_ = _s / _k
            _z_ = _z / _k
            if ex >= avg:
                p = 1
            else:
                p = -1
            result = round((p * 100.0) * math.pow(p * math.log(_s_) / math.log(_z_), powCoef) * 100.0) / 100.0
            return max(-15, result)
        except:
            return None
