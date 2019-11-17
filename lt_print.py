import asyncio, re
from slaver_spider import SlaverSpider
from login import Login
from pyppeteer import errors
from settings import STORE_INFO


async def lt_login(l, b, p):
    await p.goto("https://fuwu.taobao.com/ser/myOrderedService.htm?market=taobao")
    await p.waitForSelector("img[src='//img.alicdn.com///img.alicdn.com/bao/uploaded/TB1zQE_XtPJ3eJjSZFLSuub3FXa.jpg']")
    await p.click("img[src='//img.alicdn.com///img.alicdn.com/bao/uploaded/TB1zQE_XtPJ3eJjSZFLSuub3FXa.jpg']")

    await asyncio.sleep(3)
    p_list = await b.pages()

    print(p_list)
    page = p_list[-1]
    while 1:
        url = page.url
        print(url)
        is_mat = re.search("=http:", url)
        if not is_mat:
            await page.reload()
            await asyncio.sleep(5)
            continue
        try:
            await page.goto(url + "#/deliver")
            await page.keyboard.press("Escape")
        except Exception as e:
            pass
        else:
            break
    return page


async def lt_search(p, orderno):
    await p.focus("span.ant-input-prefix + input")
    await p.keyboard.down("ShiftLeft")
    await p.keyboard.press("Home")
    await p.keyboard.down("ShiftLeft")
    await p.keyboard.press("Delete")
    await p.type("span.ant-input-prefix + input", orderno)
    await p.keyboard.press("Enter")
    await asyncio.sleep(3)
    try:
        await p.waitForSelector(".ReactVirtualized__Grid input[type='checkbox']", timeout=5000)
    except errors.TimeoutError:
        return
    await p.click(".ReactVirtualized__Grid input[type='checkbox']")
    # await p.click("#printExpressBtn")


if __name__ == '__main__':
    # l = SlaverSpider()
    l = Login()
    loop = asyncio.get_event_loop()
    # b, p, f = loop.run_until_complete(l.login(**STORE_INFO["YK"]))
    b, p, f = loop.run_until_complete(l.login())
    new_p = loop.run_until_complete(lt_login(l, b, p))
    while True:
        orderno = input("orderNo")
        loop.run_until_complete(lt_search(new_p, orderno))
