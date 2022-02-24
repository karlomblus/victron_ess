# -*- coding: utf-8 -*
from __future__ import print_function
from __future__ import division
#from datetime import datetime, timedelta
import datetime
import calendar
import time
import json
import math
from os.path import exists
from victron_nps_localconf import *
from os import sys
import os


try:
    # For Python 3.0 and later
    from urllib.request import urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen




# Öötariif kehtib suveajal kell 24–8 ja talveajal kell 23–7    EHK GMT 21-5    edastamine 6.94 eur/kuu  +  5,08/2,95 (kmta 5.78+ 4,23/2,46)
# hetkehind: https://dashboard.elering.ee/api/nps/price/EE/current
# {  "success": true,  "data": [    {      "timestamp": 1634929200,      "price": 78.67    }  ]}
# kõige tulevikum https://dashboard.elering.ee/api/nps/price/EE/latest
# {  "success": true,  "data": [    {      "timestamp": 1635022800,      "price": 94.97    }  ]}



def vorgutasu(tt): ## tt on UTC-s, aga python väljastab tunni lokaalses ajas
    tund=int(datetime.datetime.utcfromtimestamp(tt).strftime('%H')) # ka winni arvutis õige UTC aeg
    # taastuvenergia tasu  0,0113€/kWh    Elektriaktsiis 0,001€/kWh   = 1,23+km=1,476 senti
    #print("Küsiti võrgutasu tunni",tund,"kohta")
    if (tund>=21 or tund <5): return (2.95+1.476) # soodusaeg GMT järgi
    if datetime.datetime.utcfromtimestamp(tt).weekday() >=5:  # 5 Sat, 6 Sun
        return (2.95+1.476) # nädalavahetustel ka soodus
    return (5.08+1.476) # päeva võrgutasu tariif



def download_prices(nihe,ohtuvenitus=0): # nihe on statistika tegemisel ajalukku liikumiseks
    global workdir
    gmt = time.gmtime(time.time()-nihe*86400)
    if gmt.tm_hour>=21: # kell 21 algab meil uus päev, st. uus soodusaja algus
        gmt = time.gmtime(time.time()-(nihe-1)*86400)
    
    tt_end=calendar.timegm(datetime.datetime(year=gmt.tm_year, month=gmt.tm_mon, day=gmt.tm_mday, hour=20, minute=59, second=59).timetuple())
    tt_start=tt_end-86400+1
    
    # kolm tundi enne uue soodusaja algust pärides vaatame natuke pikemalt ette. Võib juhtuda, et kell 20 on päeva kõige soodsam
    # tund laadimiseks samas 3 tundi hiljem (uus öö) on veel soodsam. Ette vaatame vaid õhtu viimastel tundidel, muidu jälle risk, et
    # üritame laadimist mitu päeva edasi lükata
    if gmt.tm_hour>=16 and gmt.tm_hour<21 and ohtuvenitus==1: 
        tt_end+=3600*5;
    
    g_start = time.gmtime(tt_start)
    g_end = time.gmtime(tt_end)
    
    #print("UTC hinnapäring vahemikus ", datetime.datetime.utcfromtimestamp( tt_start).strftime('%Y-%m-%d %H:%M:%S') , "kuni",datetime.datetime.utcfromtimestamp( tt_end).strftime('%Y-%m-%d %H:%M:%S'))
    tempdir= workdir+os.path.sep+"nps_history"
    if not os.path.exists(tempdir):
        os.mkdir(tempdir)
    
    tempfile=tempdir+os.path.sep+str(g_start.tm_year)+"-"+str("%02d" %g_start.tm_mon,)+"-"+str("%02d" %g_start.tm_mday,)+'-T'+ ("%02d" % (g_start.tm_hour,)) +'-'+str(round((tt_end-tt_start)/3600,2))+'h.txt'
    #print("tempfile: ", tempfile)
    if exists(tempfile):
        #print("Using local cache for prices")
        file = open(tempfile, "r")
        data = file.read()
        js = json.loads(data)
        try:
            ee=js['data']['ee']
            return ee
        except KeyError:
            print("WARNING: Cache failed, fetching picelist again")

    start = str(g_start.tm_year)+ '-'+ ("%02d" % (g_start.tm_mon,))+ '-'+ ("%02d" % (g_start.tm_mday,)) +'T'+ ("%02d" % (g_start.tm_hour,)) +'%3A'+ ("%02d" % (g_start.tm_min,)) +'%3A'+ ("%02d" % (g_start.tm_sec,)) +'.000Z'
    end = str(g_end.tm_year)+ '-'+ ("%02d" % (g_end.tm_mon,))+ '-'+ ("%02d" % (g_end.tm_mday,))+'T'+ ("%02d" % (g_end.tm_hour,)) +'%3A'+ ("%02d" % (g_end.tm_min,)) +'%3A'+ ("%02d" % (g_end.tm_sec,)) +'.000Z'
    print("Päring ajavahemikus",start.replace("%3A", ":"),"kuni",end.replace("%3A", ":"))

    #url = "https://dashboard.elering.ee/api/nps/price?start=2021-10-20T21%3A00%3A00.000Z&end=2021-10-21T20%3A59%3A59.999Z"
    url = "https://dashboard.elering.ee/api/nps/price?start="+start+"&end="+end
    #print("url:",url)

    response = urlopen(url)
    data = response.read().decode("utf-8")
    js = json.loads(data)

    if (not js['success']):
        print("Request failed?")
        sys.exit();

    try:
        ee=js['data']['ee']
    except KeyError:
        print("Vastuses pole ee datat?")
        sys.exit();
    #kirjutame kogu allalaetud hinna-data faili (mitte ainult EE oma)
    text_file = open(tempfile, "wt") 
    text_file.write(data)
    text_file.close()
    return ee


def sort_prices(ee):
    hinnad={}
    for key in (ee):
        tt=key['timestamp']
        pr=key['price']
        #print ("ajal " , datetime.utcfromtimestamp( tt).strftime('%Y-%m-%d %H:%M:%S') , " on hind ", round(pr/10,1),"senti + vt",vorgutasu(tt),"senti")
        pr=(pr/10)*1.20+vorgutasu(tt) # hinnad käibemaksuga
        hinnad.update({tt: pr})
    import operator
    return sorted(hinnad.items(), key=operator.itemgetter(1))  # sorteerime hindade järjekorras




def ehita_laadimislist(hinnad2,chargetime):
    invertlist=hinnad2[::-1] # keerame listi tagurpidi, kõige kallimad ajad eespool
    #tahame, et vähemalt üks chargetime oleks enne vähemalt mõnda esimest invertimet
    chargelist=hinnad2[:chargetime] # lõikeme chargelisti vastavalt lubatud laadimisajale tunde

    chargeok=0
    for pair in (chargelist):
        if int(pair[0])<invertlist[0][0] or int(pair[0])<invertlist[1][0]:  #kas on enne top2 inverlisti
            chargeok=1
            break
    # kui ei ole, siis tahame leida esimese chargetime, mis oleks enne top2 inverlisti
    if chargeok==0:
        print("Kõik laadimisajad on HILJEM kui top2 kasutamisajad. Nihutan ühe laadimisaja ettepoole")
        for pair in (hinnad2): # nüüd käime läbi kõik ajad ja leiame viimaseks laadimisajaks sobiva odava eestpoolt
            #print("Kontrollin",pair[0]," vs ",invertlist[0][0]," & ", invertlist[1][0])
            if int(pair[0])<invertlist[0][0] or int(pair[0])<invertlist[1][0]:
                print("Nihutan laadimisaja ettepoole (kallimale ajale): " ,chargelist[chargetime-1],"->",(pair[0],pair[1]))
                chargelist[chargetime-1]=(pair[0],pair[1])
                break
    return chargelist

def loaddata(dbus,a,b):
    bus = dbus.SystemBus()
    objectdata = bus.get_object(a, b)
    iface = dbus.Interface(objectdata, "com.victronenergy.BusItem")
    return iface.GetValue()

def loaddata2(a,b):
    try:
        import dbus
    except ImportError:
        print("WARNING: oleme demomasonas, dbusi pole")
        return -1
    return loaddata(dbus,a,b);

def setdata(a,b,c):
    try:
        import dbus
    except ImportError:
        print("WARNING: oleme demomasonas, dbusi pole, setData ei tööta, ",a,b,"= ",c)
        return 1
    bus = dbus.SystemBus()
    test = bus.get_object(a, b)
    iface = dbus.Interface(test, "com.victronenergy.BusItem")
    return int(iface.SetValue(c))

def leia_inverttime():
    try:
        import dbus
    except ImportError:
        print("WARNING: oleme demomasonas, dbusi pole")
        return 1
    
    soc_current=int(loaddata(dbus,'com.victronenergy.system','/Dc/Battery/Soc'))

    whleft=(soc_current-soc_minimum)* akuwh / 100
    ac_pout=int(loaddata(dbus,'com.victronenergy.system','/Ac/Consumption/L1/Power'))
    ac_pout2=ac_pout
    if ac_pout2 > 2000: # keskmine võimsus ei peaks üle 2000 olema. Ilmselt (väga?) ajutine suurem tarbimine #todo: leida reaalne keskmine
        ac_pout2=2000
    if ac_pout2 <1 : # kui toodame võrku, siis inverttime on kinda lõpmatus sel hetkel
        ac_pout2=1
    inverttime=whleft/ac_pout2
    current_soc_limit=int(loaddata2('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit'))
    print("soc_current:",soc_current,"soc_minimum:",soc_minimum,"current_soc_limit:",current_soc_limit,"whleft:",whleft,"ac_pout:",ac_pout,"inverttime:",inverttime)
    return int(math.ceil(inverttime)) # ümardame üles, soc piirist ei minda niiehknaa alla


def download_solarpredict(url):
    global workdir
    tempdir= workdir+os.path.sep+"solar_predict"
    if not os.path.exists(tempdir):
        os.mkdir(tempdir)
        
    # mind huvitav ennustus vaid soodusaja (uus päev) hetkel. Kuigi ennustus võib hommikuks täpsustuda, ei ole see enam oluline
    # sel viisil pean faili alla laadima vaid ühe korra ööpäevas ja tagantjärele tarkus mind ei huvita
    gmt = time.gmtime(time.time())
    #if gmt.tm_hour>=21: # kell 21 algab meil uus päev, st. uus soodusaja algus
    #    gmt = time.gmtime(time.time()+86400) # suht suva, kas liidan ööpäeva või 3 tundi. Mõlemal juhul saan uue kuupäeva
    
    if gmt.tm_hour>=21 or gmt.tm_hour<=6: # öisel ajal huvitab tihedam uuendus (nende arv on piiratud)
        hour=("%02d" % (gmt.tm_hour-gmt.tm_hour%3))
    else:
        hour="06"  # päeva ennustus pole oluline, jääme hommikusse kinni.

    tempfile=tempdir+os.path.sep+  str(gmt.tm_year)+"-"+str("%02d" %gmt.tm_mon,)+"-"+str("%02d" %gmt.tm_mday,)+"-"+str(hour)+'-predict.txt'
    print("tempfile: ", tempfile)
    if exists(tempfile):
        print("Using local cache for solar_predict")
        file = open(tempfile, "r")
        data = file.read()
        js = json.loads(data)
        try:
            fc=js['forecasts']
            return fc
        except KeyError:
            print("Cache failed, fetching again")

    print("fetching solar_predict")
    response = urlopen(url)
    data = response.read().decode("utf-8")
    js = json.loads(data)

    if (not js['forecasts']):
        print("WARNING: solar_predict request failed?")
        #sys.exit();

    try:
        fc=js['forecasts']
    except KeyError:
        print("WARNING: Vastuses pole solar_predict forecast datat?")
        #sys.exit();
        return ""
    #kirjutame kogu allalaetud data temp faili
    text_file = open(tempfile, "wt") 
    text_file.write(data)
    text_file.close()
    return fc


def next_solarpredict(url,selfconsume):
    if len(url)==0:
        print("WARNING: solarpredict url missing")
        return 0
    fc=download_solarpredict(url)
    if len(fc)==0:
        print("WARNING: solarpredict response failed")
        return 0

    gmt = time.gmtime(time.time())
    if gmt.tm_hour>=21: # kell 21 algab meil uus päev, st. uus soodusaja algus
        gmt = time.gmtime(time.time()+86400)
    tt_end=calendar.timegm(datetime.datetime(year=gmt.tm_year, month=gmt.tm_mon, day=gmt.tm_mday, hour=20, minute=59, second=59).timetuple())
    tt_start=tt_end-86400+1  +3600*6  # vaevalt UTC21 päike paistab, aga jätame eelmise õhtu ikkagi välja
    #print("Meid huvitab vahemik ", datetime.datetime.utcfromtimestamp( tt_start).strftime('%Y-%m-%d %H:%M:%S') , "kuni",datetime.datetime.utcfromtimestamp( tt_end).strftime('%Y-%m-%d %H:%M:%S'))
    total_est=charge_est=0;
    for x in fc:
        #print(x) # period
        end=x['period_end']
        time2=datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.%f0Z")
        tt2=calendar.timegm(time2.timetuple())
        if tt2>=tt_start and tt2 <= tt_end:
            est=x['pv_estimate']
            #print("End:",end," est:",est, " time2:", time2, "tt2:",tt2  )
            #print("see timestamp on UTC aeg:", datetime.utcfromtimestamp( tt2).strftime('%Y-%m-%d %H:%M:%S') )
            total_est+=est
            if est>((parse_isoduration(x['period'])/3600) * selfconsume/1000):
                charge_est+=est - ( (parse_isoduration(x['period'])/3600) *  selfconsume/1000)
    print ("total estimated:", total_est, "charge estimate: ", charge_est)
    return charge_est

def get_isosplit(s, split):
    if split in s:
        n, s = s.split(split)
    else:
        n = 0
    return n, s


def parse_isoduration(s):
    # Remove prefix
    s = s.split('P')[-1]
    # Step through letter dividers
    days, s = get_isosplit(s, 'D')
    _, s = get_isosplit(s, 'T')
    hours, s = get_isosplit(s, 'H')
    minutes, s = get_isosplit(s, 'M')
    seconds, s = get_isosplit(s, 'S')
    # Convert all to seconds
    dt = datetime.timedelta(days=int(days), hours=int(hours), minutes=int(minutes), seconds=int(seconds))
    return int(dt.total_seconds())


def get_current_powerprice():
    ee=download_prices(0,ohtuvenitus=0);
    lt= time.localtime(time.time())
    tt_start=int(time.mktime(datetime.datetime(year=lt.tm_year, month=lt.tm_mon, day=lt.tm_mday, hour=lt.tm_hour, minute=0, second=0).timetuple()))
    tt_end=int(time.mktime(datetime.datetime(year=lt.tm_year, month=lt.tm_mon, day=lt.tm_mday, hour=lt.tm_hour, minute=59, second=59).timetuple()))
    for key in (ee):
        tt=key['timestamp']
        pr=key['price']
        if tt >= tt_start and tt <=tt_end:
            return pr/10+vorgutasu(tt)
    print ("ERROR: ei suuda leida hetke tunnihinda")
    return -1
    

def log_statistics():
    global workdir
    logfile= workdir+os.path.sep+"data.log"
    gmt = time.gmtime(time.time())
    tt=int(time.mktime(gmt))
    inverterDbusService="com.victronenergy.vebus.ttyS4"  # com.victronenergy.system/VebusService  ?
    
    #batteryDbusService="com.victronenergy.battery.socketcan_can1"
    batteryDbusService=loaddata2("com.victronenergy.system","/Dc/Battery/BatteryService")

    AcIn1ToAcOut=round(loaddata2(inverterDbusService,'/Energy/AcIn1ToAcOut'),2)        # 181.79     <- passthru
    InverterToAcOut=round(loaddata2(inverterDbusService,'/Energy/InverterToAcOut'),2)  # 85.8158    <- akust majja
    AcIn1ToInverter=round(loaddata2(inverterDbusService,'/Energy/AcIn1ToInverter'),2)  # 92.6242    <- võrgust laadimine
    OutToInverter=round(loaddata2(inverterDbusService,'/Energy/OutToInverter'),2)      # 12.7431    <- päikesest laadimine
    AcOutToAcIn1=round(loaddata2(inverterDbusService,'/Energy/AcOutToAcIn1'),2)        # 0.309476   <- feedback päikesest
    InverterToAcIn1=round(loaddata2(inverterDbusService,'/Energy/InverterToAcIn1'),2)  # 0.218453   <- feedback akust

    soc_current=int(loaddata2('com.victronenergy.system','/Dc/Battery/Soc'))
    current_soc_limit=int(loaddata2('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit'))
    batteryLifeState=loaddata2('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/State')

    batteryMaxCellTemperature=loaddata2(batteryDbusService,'/System/MaxCellTemperature')

    currentPrice=round(get_current_powerprice(),1)

    logstring=str(tt)+ "\t" + str(AcIn1ToAcOut)+ "\t" + str(InverterToAcOut)+ "\t" + str(AcIn1ToInverter)+ "\t" + \
              str(OutToInverter)+ "\t" + str(AcOutToAcIn1)+ "\t" + str(InverterToAcIn1) + "\t" + \
              str(soc_current)+ "\t" + str(current_soc_limit)+"\t"+str(batteryLifeState)+ "\t" + \
              str(batteryMaxCellTemperature)+"\t"+str(currentPrice)
    print("log:" + logstring)

    with open(logfile,'a') as f:
        f.write(logstring+"\n")

def log_find_tt_offset(timestamp):
    logfile= workdir+os.path.sep+"data.log"
    fp=open(logfile, "rb")       # must be binary for SEEK_END
    fp.seek(-10000,os.SEEK_END)
    seensmaller=0  # kui olen korra näinud väiksemat timestampi, siis ettepoole enam ei hüppa
    fp.readline(999) #  to the end of line
    lastline=fp.readline(999).decode('ascii')
    lastpos=fp.tell()

    while True:
        curpos=fp.tell()
        #print("curpos: ",curpos)
        line=fp.readline(999).decode('ascii')
        ctt=int(line.split("\t")[0],10)
        if ctt > timestamp and seensmaller==0:  # olen liiga kaugel, hüppan suvakalt ettepoole
            fp.seek(-1000, os.SEEK_CUR)
            fp.readline(999) # poolik rida eest minema
            lastpos=fp.tell()
            lastline=fp.readline(999).decode('ascii')
        elif ctt > timestamp and seensmaller==1: # olen ühe rea üle - ÕIGE KOHT
            print("lastline: ",lastline)
            print("line: ",line)
            return lastpos
        else: # olen natuke eespool (või õige koha peal, aga tahan saada eelmiseks reaks) ja liigun ühe rea võrra eedasi
            seensmaller=1
            lastpos=curpos
            lastline=line
        


# seda scripti käivitan vaid siis, kui tahan midagi testida.
if __name__ == "__main__":
    #charge_est=next_solarpredict(solarpredict_url,1500)
    #soc_maximum2=int(round(soc_maximum - (100*charge_est*1000/akuwh)));
    #print ("Homse tootmise ennustus: ",charge_est, "confi max soc:",soc_maximum, " seega võin laadida kuni: ",soc_maximum2);
    #log_statistics()
    print(log_find_tt_offset(1644705219))


