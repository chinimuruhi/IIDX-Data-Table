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
    logging = getLogger('daily')
    manualdata_loader.set_logging(logging)
    utility.set_logging(logging)
    # textage情報の更新
    textage = textage_data(logging)
    await textage.init()
    await textage.update()

if __name__ == '__main__':
    asyncio.run(main())