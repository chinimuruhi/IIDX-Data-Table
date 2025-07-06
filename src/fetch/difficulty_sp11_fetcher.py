from common.utility import utility
import os
import gspread
import asyncio
from gspread_formatting import *
from googleapiclient.discovery import build

class difficulty_sp11_data:
    # ファイルの場所
    _FILE_PATH = './dist/difficulty/sp11'
    # ファイル名
    _FILES = {
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'difficulty': 'difficulty.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _SHEET_PATH = '1e7gdUmBk3zUGSxVGC--8p6w2TIWMLBcLzOcmWoeOx6Y'
    _SHEET_NAME = {
        'normal': 'ノーマルゲージ',
        'hard': 'ハードゲージ'
    }
    _KOJINSA_CELL = [0, 1]
    # 難易度の対応
    _TABLE_DIFFICULTY = {
        '超個人差': 12,
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
    _TITLE_DIFFICULTY = {
        'intitle':[
            ['(H)', 'H'],
            ['(L)', 'L']
        ],
        'none': 'A'
    }

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging

    # 難易度表取得
    async def update(self, textage_data):
        # シートから情報の抽出
        results = await asyncio.gather(
            self._extract_data_from_worksheet(self._SHEET_NAME['normal'], textage_data),
            self._extract_data_from_worksheet(self._SHEET_NAME['hard'], textage_data)
        )
        difficulty_dict = {
            'normal': results[0][1],
            'hard': results[1][1]
        }
        lst = []
        dct = {}
        # normalとhardの情報を結合
        for id in results[0][0].keys():
            for d in results[0][0][id].keys():
                lst.append({
                    'id': id,
                    'difficulty': d,
                    'n_value': results[0][0][id][d]['value'],
                    'h_value': results[1][0][id][d]['value']
                })
                if not id in dct:
                    dct[id] = {}
                dct[id][d] = {
                    'n_value': results[0][0][id][d]['value'],
                    'h_value': results[1][0][id][d]['value']
                }
        # ファイルへ保存
        await asyncio.gather(
            utility.save_to_file(lst, os.path.join(self._FILE_PATH, self._FILES['list'])),
            utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict'])),
            utility.save_to_file(difficulty_dict, os.path.join(self._FILE_PATH, self._FILES['difficulty']))
        )
        self._logging.info('Success in loading difficulty_sp11.')


    # worksheetから難易度情報を抽出
    async def _extract_data_from_worksheet(self, sheet_name, textage_data):
        # スプレッドシートの取得
        gc = gspread.api_key(os.getenv('GOOGLE_SHEET_KEY'))
        sheet = gc.open_by_key(self._SHEET_PATH)
        # セルの値を取得
        worksheet = sheet.worksheet(sheet_name)
        all_values = worksheet.get_all_values()
        all_colors = self._get_cell_background_colors(sheet_name, len(all_values), len(all_values[1]))
        kojinsa_color = all_colors[self._KOJINSA_CELL[0]][self._KOJINSA_CELL[1]]
        difficulty_mapping = [0] * len(all_values[1])
        difficulty_dict = {}
        songs_dict = {}
        # difficultyの生成
        for i in range(0, len(all_values[1])):
            if all_values[1][i] in self._TABLE_DIFFICULTY:
                difficulty_value = self._TABLE_DIFFICULTY[all_values[1][i]]
                # S~Fの場合は地力と個人差に分けて登録
                if difficulty_value >= 0 and difficulty_value <= 11:
                    for sub in self._SUB_DIFFICULTY:
                        difficulty_dict[str(difficulty_value - sub[0])] = sub[1] + all_values[1][i]
                else:
                    difficulty_dict[str(difficulty_value)] = all_values[1][i]
            else:
                difficulty_value = -2
                self._logging.error(all_values[1][i] + ' is not found.')
            difficulty_mapping[i] = self._TABLE_DIFFICULTY[all_values[1][i]]
        # それぞれの曲情報を取得
        for r in range(2, len(all_values)):
            for c in range(len(all_values[r])):
                if not all_values[r][c]:
                    continue
                title, difficulty = self._get_title_and_difficulty(all_values[r][c])
                id = textage_data.get_song_id(title)
                if id == -1:
                    self._logging.error('[sp11]:'+ title)
                id_str = str(id)
                # 個人差の場合に処理を変える
                if difficulty_mapping[c] >=0 and difficulty_mapping[c] <= 11:
                    if all_colors[r][c] != kojinsa_color:
                        sd = 0
                    else:
                        sd = 1
                    value = difficulty_mapping[c] - self._SUB_DIFFICULTY[sd][0]
                else:
                    value = difficulty_mapping[c]
                if not id_str in songs_dict:
                    songs_dict[id_str] = {}
                songs_dict[id_str][difficulty] = {}
                songs_dict[id_str][difficulty]['value'] = value
        return songs_dict, difficulty_dict
    
    # セルの背景色を取得
    def _get_cell_background_colors(self, sheet_name, end_row, end_col):
        # Google Sheets APIサービスを構築
        service = build('sheets', 'v4', developerKey=os.getenv('GOOGLE_SHEET_KEY'))
        cell_range = "'" + sheet_name + "'!A1:" + gspread.utils.rowcol_to_a1(end_row, end_col)
    
        # スプレッドシートデータを取得（セルのフォーマット情報を含む）
        sheet = service.spreadsheets().get(
            spreadsheetId=self._SHEET_PATH, 
            ranges=[cell_range], 
            fields="sheets.data.rowData.values.effectiveFormat.backgroundColor"
        ).execute()
    
        # 色情報を取得
        colors = []
        for r in sheet['sheets'][0]['data'][0]['rowData']:
            row = []
            for cell in r['values']:
                try:
                    color = cell['effectiveFormat']['backgroundColor']
                    rgb_code = (int(color['red'] * 255), int(color['green'] * 255), int(color['blue'] * 255)) 
                    row.append('#{:02x}{:02x}{:02x}'.format(*rgb_code))
                except:
                    row.append('#ffffff')
            colors.append(row)
        return colors
    
    # 難易度文字を含むタイトルから難易度文字を削除したタイトルと難易度を取得
    def _get_title_and_difficulty(self, title):
        for d in self._TITLE_DIFFICULTY['intitle']:
            if d[0] in title:
                return title.replace(d[0], ''), d[1]
        return title, self._TITLE_DIFFICULTY['none']
                
                

            




        
        
