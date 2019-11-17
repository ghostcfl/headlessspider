import asyncio
from slaver_spider import SlaverSpider

if __name__ == '__main__':
    s = SlaverSpider()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(s.run_order_detail_spider())
