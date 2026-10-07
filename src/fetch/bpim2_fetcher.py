from common.utility import utility
import os
import asyncio
import math
import json
import re

class bpim2_data:
    # ファイルの場所
    _FILE_PATH = './dist/bpim2'
    # ファイル名
    _FILES = {
        'sp_list':'sp_list.json',
        'sp_dict':'sp_dict.json',
        'etag': 'etag.txt'
    }
    # データ取得先
    _URLS = {
        'songs':'https://bpi2.poyashi.me/api/v2/songs'
    }
    _DIFFICULTY_MAP = {
        'HYPER': 'H',
        'ANOTHER': 'A',
        'LEGGENDARIA': 'L'
    }
    # textageのURL(例: 28/_65c.html?1AC00)からtagを抽出
    _PATTERN_TEXTAGE_TAG = re.compile(r'^[^/]+/(.+?)\.html')
    _SCORE_RATE = {
        'AAA': 8.0/9.0,
        'MAX_MINUS': 17.0/18.0
    }
    # BPI V2のモデル定数
    # 参考：https://github.com/BPIManager/BPIManager2/blob/main/src/constants/iidx/newBpi/modelConstants.ts
    _V2_Z0 = -0.19383932671707751
    _V2_Z100_MEDIAN = 6.516395340703802
    _V2_Z_REF = 1.9481138704797247
    _V2_Z100_IQR = 1.1916
    _V2_COEF_MEDIAN = 0.949
    _V2_BPI_FLOOR = -15
    _V2_GAMMA_CLAMP = (0.3, 3.0)
    _V2_CURVE_EXP_CLAMP = (0.62, 3.0)

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        os.makedirs(self._FILE_PATH, exist_ok=True)

    # BPI定義の取得
    async def update(self, textage_data):
        # Last-Modifiedが返らないためETagで更新を判定
        etag_path = os.path.join(self._FILE_PATH, self._FILES['etag'])
        headers = {}
        if os.path.exists(etag_path):
            with open(etag_path, mode='r', encoding='utf_8') as f:
                headers['If-None-Match'] = f.read()
        res = await utility.requests_get(self._URLS['songs'], headers)
        # 200 OKの場合
        if res.status_code == 200:
            songs = json.load(res)['body']
            sp_list = []
            sp_dict = {}
            for song in songs:
                # IDを取得(textageのtag優先、取得できない場合は曲名から)
                id = -1
                match = self._PATTERN_TEXTAGE_TAG.match(song['textage'] or '')
                if match:
                    id = textage_data.get_song_id_by_textage_tag(match.group(1))
                if id == -1:
                    id = textage_data.get_song_id(song['title'])
                if id == -1:
                    self._logging.error('[bpim2]:'+ song['title'])
                id_str = str(id)
                # 難易度の変換
                difficulty = self._DIFFICULTY_MAP[song['difficulty']]
                level = int(song['difficultyLevel'])
                wr = int(song['wrScore'])
                avg = int(song['kaidenAvg'])
                notes = int(song['notes'])
                bpm = song['bpm']
                coef = song['coef']
                mu = song['mu']
                sigma = song['sigma']
                # BPIの計算
                aaa_bpi = self._calculate_bpi(wr, notes, 'AAA', coef, mu, sigma)
                max_minus_bpi = self._calculate_bpi(wr, notes, 'MAX_MINUS', coef, mu, sigma)
                if aaa_bpi is None or max_minus_bpi is None:
                    self._logging.error('BPIM2 Load Skip(1): ' + song['title'] + '[' + song['difficulty'] + ']')
                    continue
                # データの成形
                elm_dict = {
                    'level': level,
                    'wr': wr,
                    'avg': avg,
                    'notes': notes,
                    'bpm': bpm,
                    'coef': coef,
                    'mu': mu,
                    'sigma': sigma,
                    'aaa_bpi': aaa_bpi,
                    'max_minus_bpi': max_minus_bpi
                }
                elm_list = {
                    'id': id,
                    'difficulty': difficulty,
                    **elm_dict
                }
                if not id_str in sp_dict:
                    sp_dict[id_str] = {}
                if not difficulty in sp_dict[id_str]:
                    sp_dict[id_str][difficulty] = elm_dict
                    sp_list.append(elm_list)
                else:
                    self._logging.error('BPIM2 Load Skip(2): ' + song['title'] + '[' + song['difficulty'] + ']')
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(sp_list, os.path.join(self._FILE_PATH, self._FILES['sp_list'])),
                utility.save_to_file(sp_dict, os.path.join(self._FILE_PATH, self._FILES['sp_dict'])),
            )
            if 'ETag' in res.headers:
                with open(etag_path, mode='w', encoding='utf_8') as f:
                    f.write(res.headers['ETag'])
            self._logging.info('Success in loading bpim2.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('bpim2 was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch bpim2.')

    # BPI V2(分布ベース)の計算
    # 参考：https://github.com/BPIManager/BPIM-bpicalc/blob/main/src/v2.ts
    def _t(self, score, max_score):
        miss = max(0.5, max_score - min(max(score, 0), max_score))
        return -math.log(miss)

    def _clamp(self, x, lo, hi):
        return max(lo, min(hi, x))

    def _gamma(self, z100):
        z0 = self._V2_Z0
        g_ref = self._V2_Z100_MEDIAN - z0
        g_song = z100 - z0
        r_typ = (self._V2_Z_REF - z0) / g_ref
        r_song = (self._V2_Z_REF - z0) / g_song
        if r_typ <= 0 or r_typ >= 1 or r_song <= 0 or r_song >= 1:
            return 1.0
        clamped = self._clamp(math.log(r_typ) / math.log(r_song), *self._V2_GAMMA_CLAMP)
        d = abs(z100 - self._V2_Z100_MEDIAN) / self._V2_Z100_IQR
        w = (d * d) / (d * d + 1)
        return 1 + w * (clamped - 1)

    def _calculate_bpi(self, wr, notes, score_rate, coef, mu, sigma):
        try:
            if mu is None or sigma is None or notes == 0:
                return None
            max_score = notes * 2
            z0 = self._V2_Z0
            z100 = (self._t(wr, max_score) - mu) / sigma
            if abs(z100 - z0) < 1e-9:
                return None
            if coef is None:
                coef = self._V2_COEF_MEDIAN
            k = self._clamp(self._gamma(z100) * coef, *self._V2_CURVE_EXP_CLAMP)
            ex = math.ceil(max_score * self._SCORE_RATE[score_rate])
            z = (self._t(ex, max_score) - mu) / sigma
            ratio = (z - z0) / (z100 - z0)
            bpi = 100 * math.copysign(1, ratio) * math.pow(abs(ratio), k)
            # JavaScriptのMath.roundに合わせて四捨五入
            return max(self._V2_BPI_FLOOR, math.floor(bpi * 100 + 0.5) / 100)
        except:
            return None
