import asyncio, re, random
from pyppeteer.launcher import launch
from pyppeteer import errors
from settings import launch_setting, LINUX, pic_mail_recevier
from Format import sleep, net_check, time_now
from logger import get_logger
from smtp import mail_pic
from matplotlib import pyplot as plt, image as mpimg

# from spider import Spider

logger = get_logger()


class Login(object):
    b = None

    async def get_page(self):
        self.b = await launch(**launch_setting)
        p = await self.b.pages()
        p = p[0]
        await p.setViewport({"width": 1440, "height": 790})
        return p

    async def login(self):
        p = await self.get_page()
        while 1:
            try:
                await p.goto("https://login.taobao.com", timeout=30000)
            except errors.PageError:
                logger.warning("网络异常5秒后重连")
                sleep(5)
            except errors.TimeoutError:
                logger.warning("网络异常5秒后重连")
                sleep(5)
            else:
                break

        ms = await p.J(".module-static")
        if ms:
            ls = await p.J(".login-switch")
            box = await ls.boundingBox()
            await p.mouse.click(box['x'] + 10, box['y'])

        while 1:
            try:
                await p.waitForSelector("#J_QRCodeImg")
                image = await p.J("#J_QRCodeImg")
                await image.screenshot({'path': './qrcode.png'})
            except errors.NetworkError as e:
                # logger.warning(str(e))
                pass
            else:
                break

        if LINUX:
            mail_pic(pic_mail_recevier.split(","))
        else:
            logger.info("扫码登陆")
            qrcode = mpimg.imread('qrcode.png')  # 读取和代码处于同一目录下的 qrcode.png
            plt.imshow(qrcode)  # 显示图片
            plt.axis('off')  # 不显示坐标轴
            plt.show()

        f = await self.phone_verify(p)
        return self.b, p, f

    async def phone_verify(self, p):
        try:
            await p.waitForSelector("#container", timeout=120000)
        except errors.TimeoutError:
            logger.info("超时末扫码或需要手机验证！")
            await self.verify(p)
            net_check()
            await p.goto("https://myseller.taobao.com/home.htm")
        finally:
            await p.waitForSelector("#container", timeout=30000)
            content = await p.content()
            a = re.search('nick: "(.*?):', content)
            b = re.search('nick: "(.*?)"', content)
            if a:
                account = a.group(1)
            else:
                account = b.group(1)
            if account == "arduino_sz":
                logger.info("开源电子登陆成功")
                f = "KY"
            elif account == "玉佳电子科技有限公司":
                logger.info("玉佳企业店登陆成功")
                f = "YK"
            elif account == "simpleli":
                logger.info("赛宝电子登陆成功")
                f = "TB"
            elif account == "selingna5555":
                logger.info("玉佳电子登陆成功")
                f = "YJ"
            else:
                logger.info('登陆账户信息获取失败，即将重启爬虫！')
                await self.b.close()
                await self.login()
            try:
                net_check()
                await p.goto("https://trade.taobao.com/trade/itemlist/list_sold_items.htm")
                await p.waitForSelector(".pagination-mod__show-more-page-button___txdoB", timeout=30000)
            except errors.TimeoutError:
                await self.verify(p)
                net_check()
                await p.goto("https://trade.taobao.com/trade/itemlist/list_sold_items.htm")
                await p.waitForSelector(".pagination-mod__show-more-page-button___txdoB", timeout=30000)
            finally:
                net_check()
                await p.click(".pagination-mod__show-more-page-button___txdoB")  # 显示全部页码
                await self.slider(p)
                return f

    async def get_nc_frame(self, frames):
        for frame in frames:
            slider = await frame.J("#nc_1_n1z")
            if slider:
                return frame
        return None

    async def slider(self, p):
        await asyncio.sleep(3)
        frames = p.frames
        frame = await self.get_nc_frame(frames)
        if frame:
            nc = await frame.J("#nc_1_n1z")
            nc_detail = await nc.boundingBox()
            print(nc_detail)
            x = int(nc_detail['x'] + 1)
            y = int(nc_detail['y'] + 1)
            width = int(nc_detail['width'] - 1)
            height = int(nc_detail['height'] - 1)
            # input(":")
            logger.info("条形验证码")
            while 1:
                await asyncio.sleep(1)
                start_x = random.uniform(x, x + width)
                start_y = random.uniform(y, y + height)
                a = y - start_y
                # await frame.hover("#nc_1_n1z")
                await p.mouse.move(start_x, start_y)
                await p.mouse.down()
                await p.mouse.move(start_x + random.uniform(300, 400),
                                   start_y + random.uniform(a, 34 - abs(a)),
                                   {"steps": random.randint(30, 100)})
                await p.mouse.up()
                try:
                    frame.waitForSelector(".nc-lang-cnt a", timeout=10000)
                    await asyncio.sleep(2)
                    await frame.click(".nc-lang-cnt a")
                except errors.TimeoutError:
                    await asyncio.sleep(1)
                    slider = await frame.J("#nc_1_n1z")
                    if not slider:
                        break
                except errors.PageError:
                    await asyncio.sleep(1)
                    slider = await frame.J("#nc_1_n1z")
                    if not slider:
                        break

    async def verify(self, p):
        try:
            await p.waitForSelector("div.aq_overlay_mask", timeout=10000)
        except errors.TimeoutError:
            pass
        else:
            logger.info("需要要手机验证码")
            await asyncio.sleep(10)
            frames = p.frames
            net_check()
            await frames[1].click(".J_SendCodeBtn")
            a = input(time_now() + " | 请输入6位数字验证码：")
            await frames[1].type(".J_SafeCode", a, {'delay': self.input_time_random() - 50})
            net_check()
            await frames[1].click("#J_FooterSubmitBtn")

    def input_time_random(self):
        return random.randint(100, 151)
