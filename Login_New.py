import asyncio
import time
import random
from pyppeteer.launcher import launch  # 控制模拟浏览器用
from retrying import retry  # 设置重试次数用的
from pyppeteer import errors
from settings import STORE_INFO

width, height = 1600, 900
login_url = "https://login.taobao.com/"
launch_setting = {
    'executablePath': '.\\chrome-win\\chrome.exe',
    'headless': False,
    'autoClose': True,
    'dumpio': True,
    'args': [f'--window-size={width},{height}', '--disable-infobars', '--no-sandbox'],
    # 'userDataDir': './userdata',
}


async def get_page_class():
    """
    起动浏览器并返回一个page类对象
    :return: page
    """
    browser = await launch(launch_setting)  # 启动pyppeteer 属于内存中实现交互的模拟器
    page = await browser.newPage()  # 启动个新的浏览器页面
    return page


def get_store_info(i):
    """
    获取店铺的登陆信息
    :return: username, password, fromStore
    """
    username = STORE_INFO[i]['username']
    password = STORE_INFO[i]['password']
    fromStore = STORE_INFO[i]['fromStore']
    return username, password, fromStore


async def login(page, username, password, fromStore):
    await page.setViewport({'width': width, 'height': height})
    await page.goto(login_url)  # 访问登录页面
    await page_evaluate(page)  # 执行JS修改浏览器携带属性
    try:
        await page.waitForSelector('.forget-pwd.J_Quick2Static', timeout=3000)
        await page.click('.forget-pwd.J_Quick2Static')
    except errors.TimeoutError:
        print("没有发现按钮")
    except errors.ElementHandleError:
        print("没有发现按钮")
    finally:
        await page.type('#TPL_username_1', username, {'delay': input_time_random() - 50})
        await page.type('#TPL_password_1', password, {'delay': input_time_random()})
    # await page.screenshot({'path': './screenshot/headless-test-result.png'})
    await page.waitFor(2)
    # 检测页面是否有滑块。原理是检测页面元素。
    slider = await page.Jeval('#nocaptcha', 'node => node.style')  # 是否有滑块
    if slider:
        print("出现滑块情况判定")
        while True:
            print("刷新")
            # 用于滑动失败刷新
            flag, page = await mouse_slide(page=page)
            # await page.screenshot({'path': './headless-test-result.png'})
            fresh = ''
            try:
                fresh = await page.Jeval('.errloading', 'node => node.textContent')
            except Exception:
                pass
            if fresh:
                await page.hover('a[href="javascript:noCaptcha.reset(1)"]')
                await page.mouse.down()
                await page.mouse.up()
                time.sleep(1)
            else:
                break
        if flag:
            # await page.keyboard.press('Enter')  # 确保内容输入完毕，少数页面会自动完成按钮点击
            # print("print enter", flag)
            await page.click("#J_SubmitStatic")  # 调用page模拟点击登录按钮。
            time.sleep(2)
            await get_cookie(page)
    else:
        print("")
        # await page.keyboard.press('Enter')
        # print("print enter")
        await page.click("#J_SubmitStatic")
        await page.waitFor(20)
        await page.waitForNavigation()
    await page.waitForSelector("#qn-workbench-head", timeout=0)
    try:
        await page.waitForSelector(".indexnotice-step-1JI8T", timeout=15)  # 等待淘宝后台的加载
        await page.click(".indexnotice-step-1JI8T")  # 点掉后台弹出的窗体
    except errors.TimeoutError:
        pass
    return page, fromStore


async def page_evaluate(page):
    """
    替换淘宝在检测浏览时采集的一些参数。
    就是在浏览器运行的时候，始终让window.navigator.webdriver=false
    navigator是window对象的一个属性，同时修改plugins，languages，navigator
    以下为插入中间js，将淘宝会为了检测浏览器而调用的js修改其结果。
    """
    await page.evaluate('''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => undefined } }) }''')
    await page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
    await page.evaluate(
        '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
    await page.evaluate(
        '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')


async def get_cookie(page):
    """获取登录后cookie"""
    cookies_list = await page.cookies()
    cookies = ''
    for cookie in cookies_list:
        str_cookie = '{0}={1};'
        str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
        cookies += str_cookie
    return cookies


def retry_if_result_none(result):
    return result is None


@retry(retry_on_result=retry_if_result_none, )
async def mouse_slide(page=None, frame=None):
    await asyncio.sleep(2)
    try:
        # 鼠标移动到滑块，按下，滑动到头（然后延时处理），松开按键
        if frame:
            await frame.hover('#nc_1_n1z')
        else:
            await page.hover('#nc_1_n1z')
            await page.mouse.down()
            await page.mouse.move(2000, 0, {'delay': random.randint(1000, 2000)})
            await page.mouse.up()
    except Exception as e:
        print(e, ':验证失败')
        return None, page
    else:
        await asyncio.sleep(2)
        # 判断是否通过
        slider_again = ''
        try:
            slider_again = await page.Jeval('.nc-lang-cnt', 'node => node.textContent')
        except:
            pass
        if slider_again != '验证通过':
            return None, page
        else:
            print('验证通过')
            return 1, page


def input_time_random():
    return random.randint(100, 151)


if __name__ == '__main__':
    page = asyncio.get_event_loop().run_until_complete(get_page_class())
    for i in range(2):
        username, password, fromStore = get_store_info(i)
        page1, fromStore1 = asyncio.get_event_loop().run_until_complete(login(page, username, password, fromStore))
        while True:
            pass
    # print(fromStore1)
