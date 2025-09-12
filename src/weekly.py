from dotenv import load_dotenv
import json
import asyncio
from logging import getLogger, config

from common.manualdata_loader import manualdata_loader
from common.utility import utility
from fetch.textage_fetcher import textage_data
from fetch.difficulty_sp12_fetcher import difficulty_sp12_data
from fetch.difficulty_sp11_fetcher import difficulty_sp11_data
from fetch.cpi_fetcher import cpi_data
from fetch.konami_fetcher import konami_data
from fetch.bpi_fetcher import bpi_data
from fetch.notes_radar_fetcher import notes_radar_data
from fetch.difficulty_dp_fetcher import difficulty_dp_data
from fetch.ereter_fetcher import ereter_data

async def main():
    # 検証環境の.envを読み込み
    load_dotenv()
    # logger設定の読み込み
    with open('./src/log_config.json', 'r') as f:
        log_conf = json.loads(f.read())
        config.dictConfig(log_conf)
    logging = getLogger('weekly')
    manualdata_loader.set_logging(logging)
    utility.set_logging(logging)
    # textage情報の更新
    textage = textage_data(logging)
    await textage.init()
    await textage.update()
    # 各種fetcherの作成
    sp12 = difficulty_sp12_data(logging)
    sp11 = difficulty_sp11_data(logging)
    cpi = cpi_data(logging)
    konami = konami_data(logging)
    bpi  = bpi_data(logging)
    notes_radar = notes_radar_data(logging)
    dp = difficulty_dp_data(logging)
    ereter = ereter_data(logging)
    # 各種情報の取得
    await asyncio.gather(
        sp12.update(textage),
        sp11.update(textage),
        cpi.update(textage),
        konami.update(textage),
        bpi.update(textage),
        notes_radar.update(textage),
        dp.update(textage),
        ereter.update(textage)
    )

if __name__ == '__main__':
    asyncio.run(main())