import asyncio, shutil
from slaver_spider import SlaverSpider
# from pyppeteer.launcher import CHROME_PROFILE_PATH

if __name__ == '__main__':
    # shutil.rmtree(CHROME_PROFILE_PATH, True)
    s = SlaverSpider()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(s.run_link_spider())
