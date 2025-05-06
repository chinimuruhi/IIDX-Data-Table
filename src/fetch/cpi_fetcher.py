from common.utility import utility
from bs4 import BeautifulSoup
import os
import requests
import re
import asyncio

class cpi_data:
    # ファイルの場所
    _FILE_PATH = './dist/cpi'
    # ファイル名
    _FILES = {
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://cpi.makecir.com/scores/tables'
    }
    _ID_REGREX = re.compile(r'/scores/view/([0-9]+)')
    _VALUE_STRIP = '/'
    _VALUE_REPLACE = [
        ['inf', -1],
        ['-', -2]
    ]
    _TITLE_DIFFICULTY = {
        'intitle':[
            ['[H]', 'H'],
            ['[L]', 'L'],
            ['[A]', 'A']
        ],
        'none': 'A'
    }

    def __init__(self, logging):
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
    
    # 難易度表取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        if res.status_code == requests.codes.ok:
            # 200 OKの場合
            # htmlから情報を抽出
            soup = BeautifulSoup(res.text, 'html.parser')
            easy_table = soup.find('table', id='easy_table')
            clear_table = soup.find('table', id='clear_table')
            hard_table = soup.find('table', id='hard_table')
            exh_table = soup.find('table', id='exh_table')
            fc_table = soup.find('table', id='fc_table')
            results = await asyncio.gather(
                self._table_json(easy_table, textage_data),
                self._table_json(clear_table, textage_data),
                self._table_json(hard_table, textage_data),
                self._table_json(exh_table, textage_data),
                self._table_json(fc_table, textage_data)
            )
            # listとdictに成形
            dct = {}
            lst = []
            for id in results[0].keys():
                id_str = id
                for difficulty in results[0][id].keys():
                    if not id_str in dct:
                        dct[id_str] = {}
                    dct[id_str]['cpi_id'] = results[0][id][difficulty]['cpi_id']
                    # dict
                    dct[id_str][difficulty] = {
                        'easy':{
                            'cpi_value': results[0][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[0][id][difficulty]['kojinsa_value']
                        },
                        'clear':{
                            'cpi_value': results[1][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[1][id][difficulty]['kojinsa_value']
                        },
                        'hard':{
                            'cpi_value': results[2][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[2][id][difficulty]['kojinsa_value']
                        },
                        'exh':{
                            'cpi_value': results[3][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[3][id][difficulty]['kojinsa_value']
                        },
                        'fc':{
                            'cpi_value': results[4][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[4][id][difficulty]['kojinsa_value']
                        },
                    }
                    # list
                    lst.append({
                        'id': id,
                        'difficulty': difficulty,
                        'easy':{
                            'cpi_value': results[0][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[0][id][difficulty]['kojinsa_value']
                        },
                        'clear':{
                            'cpi_value': results[1][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[1][id][difficulty]['kojinsa_value']
                        },
                        'hard':{
                            'cpi_value': results[2][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[2][id][difficulty]['kojinsa_value']
                        },
                        'exh':{
                            'cpi_value': results[3][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[3][id][difficulty]['kojinsa_value']
                        },
                        'fc':{
                            'cpi_value': results[4][id][difficulty]['cpi_value'],
                            'kojinsa_value': results[4][id][difficulty]['kojinsa_value']
                        }
                    })
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(lst, os.path.join(self._FILE_PATH, self._FILES['list'])),
                utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading cpi.')
        elif res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            self._logging.info('cpi was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch cpi.')
    
    # HTMLのtableからJSONに変換する
    async def _table_json(self, table, textage_data):
        songs = table.find_all('td', {'class': 'table-elem'})
        result = {}
        for song in songs:
            a = song.find('a')
            cpi_id = self._ID_REGREX.findall(a['href'])[0][0]
            div = song.find('div')
            cpi_values = div.get_text(strip=True).split(self._VALUE_STRIP)
            for i in range(len(cpi_values)):
                cpi_values[i] = cpi_values[i].strip()
                for r in self._VALUE_REPLACE:
                    if cpi_values[i] == r[0]:
                        cpi_values[i] = r[1]
                        break
                else:
                    try:
                        cpi_values[i] = float(cpi_values[i])
                    except:
                        self._logging('Faild to load cpi_values')
                        cpi_values[i] = -3            
            title, difficulty = self._get_title_and_difficulty(a.get_text(strip=True))
            id = textage_data.get_song_id(title)
            if id == -1:
                self._logging.error('[cpi]:'+ title)
            if not id in result:
                result[id] = {}
            result[id][difficulty] = {
                'cpi_id': cpi_id,
                'cpi_value': cpi_values[0],
                'kojinsa_value': cpi_values[1]
            }
        return result
    

    # 難易度文字を含むタイトルから難易度文字を削除したタイトルと難易度を取得
    def _get_title_and_difficulty(self, title):
        for d in self._TITLE_DIFFICULTY['intitle']:
            if d[0] in title:
                return title.replace(d[0], ''), d[1]
        return title, self._TITLE_DIFFICULTY['none']