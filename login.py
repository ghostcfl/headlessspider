import asyncio, re
from pyppeteer.launcher import launch
from pyppeteer.errors import TimeoutError
from settings import launch_setting, login_url, width, height, launch_setting_dev
from smtp import mail_pic

class Login(object):

    def __init__(self):
        self.browser = asyncio.get_event_loop().run_until_complete(launch(launch_setting))
        self.page = asyncio.get_event_loop().run_until_complete(self.browser.newPage())

    async def login(self):
        await self.page.setViewport({'width': width, 'height': height})
        await self.page_evaluate(self.page)
        await self.page.goto(login_url)
        try:
            await self.page.waitForSelector("#J_Static2Quick", visible=True, timeout=1000)
            await self.page.click("#J_Static2Quick")  # 切换到扫码页面
        except TimeoutError:
            pass
        finally:
            image_element = await self.page.querySelector("#J_QRCodeImg")
            await image_element.screenshot({'path': './qrcode.png'})
            email = input("输入接收登陆二维码的邮箱")
            mail_pic(email.split(","))
        await self.page.waitForSelector("#container", timeout=0)
        content = await self.page.content()
        account = re.search('nick: "(.*?)",', content).group(1)
        # print(account)
        if account == "arduino_sz:test":
            print("开源电子登陆成功")
            fromStore = "KY"
        elif account == "玉佳电子科技有限公司:test":
            print("玉佳企业店登陆成功")
            fromStore = "YK"
        return self.browser, self.page, fromStore

    async def get_cookies(self):
        return await self.page.cookies()

    async def page_evaluate(self, page):
        """
        替换淘宝在检测浏览时采集的一些参数。
        就是在浏览器运行的时候，始终让window.navigator.webdriver=false
        navigator是window对象的一个属性，同时修改plugins，languages，navigator
        以下为插入中间js，将淘宝会为了检测浏览器而调用的js修改其结果。
        """
        await page.evaluateOnNewDocument('() =>{ Object.defineProperties(navigator,'
                                         '{ webdriver:{ get: () => false } }) }')  # 本页刷新后值不变
        # await self.page.evaluate(
        #     '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => undefined } }) }''')
        # await self.page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
        # await self.page.evaluate(
        #     '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
        # await self.page.evaluate(
        #     '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(Login().login())
    # asyncio.get_event_loop().run_until_complete(Login().get_page())
