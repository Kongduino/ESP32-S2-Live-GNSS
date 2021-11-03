from machine import UART
import network, time
from machine import Pin
import ujson
import urequests
from tftlcd import LCD32

RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,0,255)
BLACK = (0,0,0)
WHITE = (255,255,255)
d = LCD32(portrait=1)
d.fill(BLACK)
lastLatitude = 0.0
lastLongitude = 0.0
KEY=Pin(0, Pin.IN, Pin.PULL_UP) #构建KEY对象
zoom=12
My_APY_Key="xxxxxxxxxx"
#MapQuest API Key
#https://developer.mapquest.com/plan_purchase/steps/business_edition/business_edition_free/register
#免費加入,一個月15萬筆交易  

def displayTime(t):
    global d
    d.printStr('Time: '+t, 0, 300, BLUE, size=1)
def displayDate(t):
    global d
    d.printStr(t, 120, 300, BLUE, size=1)

def getMap(lat, p0, long, p1):
    if p0==b'S':
        lat = lat * -1
        if p1==b'W':
            long = long * -1
    url = 'https://www.mapquestapi.com/staticmap/v5/map?key=USEYOUROWNKEY&center=xxLATxx,xxLONGxx&size=240,340&zoom=xxZOOMxx&size=@2x&locations=xxLATxx,xxLONGxx|marker-start'
    url = url.replace('xxLONGxx', str(long), 2)
    url = url.replace('xxLATxx', str(lat), 2)
    url = url.replace('USEYOUROWNKEY', My_APY_Key)
    url = url.replace('xxZOOMxx', zoom)
    print(url)
    re=urequests.get(url)
    print("getMap: "+str(re.status_code))
    if re.status_code == 200:
        with open('image.jpg', 'wb') as fp:
            fp.write(re.content)
            fp.close()
        d.Picture(0, 0, "/image.jpg")
    else:
        print("Couldn't load map!")
    re.close()
    for y in range(300,320):
        d.drawLine(0,y,240,y, BLACK) #顯示日期和時間嘅空間

def parseDegrees(term):
  value = float(term) / 100.0
  left = int(value)
  value = (value - left) * 1.66666666666666
  value += left
  return value

def parseZDA(result):
    global lastLatitude, lastLongitude
    if len(result)<7:
        return
    if result[1] != b'':
        s=result[1][0:2]+b':'+result[1][2:4]+b':'+result[1][4:6]
        print(b'UTC Time [ZDA]: '+s)
        displayTime(s.decode())
        s=result[4]+b'/'+result[3]+b'/'+result[2]
        print(b'UTC Date [ZDA]: '+s)
        displayDate(s.decode())

def parseGGA(result):
    global lastLatitude, lastLongitude
    if len(result)<15:
        return
    if result[1] != b'':
        print(b'UTC Time [GGA]: '+result[1][0:2]+b':'+result[1][2:4]+b':'+result[1][4:6])
    if result[2] != b'':
        latitude = float('%.8f'%parseDegrees(result[2]))
        longitude = float('%.8f'%parseDegrees(result[4]))
        print("Coordinates: {} {}, {} {}".format(latitude, result[3].decode(), longitude, result[5].decode()))
        if abs(latitude-lastLatitude)>0.01 or abs(longitude-lastLongitude)>0.01:
            lastLatitude=latitude
            lastLongitude=longitude
            getMap(latitude, result[3], longitude, result[5])

def parseGLL(result):
    global lastLatitude, lastLongitude
    if len(result)<7:
        return
    if result[5] != b'':
        print(b'UTC Time [GLL]: '+result[5][0:2]+b':'+result[5][2:4]+b':'+result[5][4:6])
    if result[1] != b'':
        latitude = float('%.8f'%parseDegrees(result[1]))
        longitude = float('%.8f'%parseDegrees(result[3]))
        print("Coordinates: {} {}, {} {}".format(latitude, result[2].decode(), longitude, result[4].decode()))
        if abs(latitude-lastLatitude)>0.01 or abs(longitude-lastLongitude)>0.01:
            lastLatitude=latitude
            lastLongitude=longitude
            getMap(latitude, result[2], longitude, result[4])

def parseRMC(result):
    global lastLatitude, lastLongitude
    if len(result)<11:
        return
    if result[1] != b'':
        print(b'UTC Time [RMC]: '+result[5][0:2]+b':'+result[5][2:4]+b':'+result[5][4:6])
    if result[2] == b'A':
        latitude = float('%.8f'%parseDegrees(result[3]))
        longitude = float('%.8f'%parseDegrees(result[5]))
        print("Coordinates: {} {}, {} {}".format(latitude, result[4].decode(), longitude, result[6].decode()))
        if abs(latitude-lastLatitude)>0.01 or abs(longitude-lastLongitude)>0.01:
            lastLatitude=latitude
            lastLongitude=longitude
            getMap(latitude, result[4], longitude, result[6])

def parseGSV(result):
    try:
        if result[1] != b'':
            print ("Message {} / {}. SIV: {}".format(result[2].decode(), result[1].decode(), result[3].decode()))
    except:
        print(b', '.join(result))


def WIFI_Connect():
    with open('wifisecret.json') as fp:
        #{"SSID":"01Studio", "pwd":"88888888"}
        #請填表你嘅網絡名同密碼
        data = ujson.loads(fp.read())
    fp.close()
    
    WIFI_LED=Pin(2, Pin.OUT) #初始化WIFI指示灯
    wlan = network.WLAN(network.STA_IF) #STA模式
    wlan.active(True)                   #激活接口
    start_time=time.time()              #记录时间做超时判断
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(data['SSID'], data['pwd']) #输入WIFI账号密码
        while not wlan.isconnected():
            #LED闪烁提示
            WIFI_LED.value(1)
            time.sleep_ms(300)
            WIFI_LED.value(0)
            time.sleep_ms(300)
            #超时判断, 15秒没连接成功判定为超时
            if time.time()-start_time > 15 :
                print('WIFI Connected Timeout!')
                break
    if wlan.isconnected():
        #LED点亮
        WIFI_LED.value(1)
        #串口打印信息
        print('network information:')
        print(' IP: '+wlan.ifconfig()[0])
        print(' Subnet: '+wlan.ifconfig()[1])
        print(' GW: '+wlan.ifconfig()[2])

uart=UART(1, 9600, rx=9, tx=8)
print("Starting wifi...")
WIFI_Connect()

#先顯示北京地圖 :-)
getMap(39.871962, b'N', 116.400928, b'E')
remainder = b''
Buffer = []
waitForDollar = True
while True:
    if KEY.value()==0: #按键被按下
        time.sleep_ms(10) #消除抖动
        if KEY.value()==0: #确认按键被按下
            zoom = zoom + 1
            if zoom > 14:
                zoom = 10
            print('zoom: '+str(zoom))
            while not KEY.value(): #检测按键是否松开
                pass
            lastLatitude = 0.0
    if uart.any():
        #print("Incoming!")
        text = remainder
        while uart.any():
            text = text + uart.read(64) #接收128个字符
        remainder = b''
        print(text)
        if waitForDollar == True:
            j=len(text)
            for i in range(0, j-1):
                if text[i] == 36:
                    print("Valid sentence starts at "+str(i))
                    waitForDollar = False
                    break
            if waitForDollar == True:
                print("Still no dollar!")
            else:
                text=text[i:].splitlines()
                for x in text:
                    Buffer.append(x)
                #remainder = Buffer.pop() # the last last may not be complete
                waitForDollar = True
        Buffer.reverse()
        while len(Buffer)>0:
            x = Buffer.pop()
            chunks = x.split(b',')
            verb = chunks[0]
            if len(verb) == 6:
                verb=verb[3:]
                if verb == b'GGA':
                    parseGGA(chunks)
                if verb == b'ZDA':
                    parseZDA(chunks)
                elif verb == b'GLL':
                    parseGLL(chunks)
                elif verb == b'GSV':
                    parseGSV(chunks)
                elif verb == b'RMC':
                    parseRMC(chunks)
                else:
                    print(x)
        #print("Buffer empty")