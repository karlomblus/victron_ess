# -*- coding: utf-8 -*
from __future__ import print_function
from __future__ import division
from victron_nps_utils import *
import json
from datetime import datetime
import time


if not os.path.exists(workdir):
    print ("Working directory not exists. WILL DIE NOW");
    sys.exit();

lt= time.localtime(time.time())
print("local time:",lt)


# localtimest saab winni masinas GMT timestamp  victronis on mõlemad GMT-s ja saab ka õige timestampi
tt_start=int(time.mktime(datetime(year=lt.tm_year, month=lt.tm_mon, day=lt.tm_mday, hour=lt.tm_hour, minute=0, second=0).timetuple()))
tt_end=int(time.mktime(datetime(year=lt.tm_year, month=lt.tm_mon, day=lt.tm_mday, hour=lt.tm_hour, minute=59, second=59).timetuple()))
print("Hetke UTC aeg on vahemikus ", datetime.utcfromtimestamp( tt_start).strftime('%Y-%m-%d %H:%M:%S') , "kuni",datetime.utcfromtimestamp( tt_end).strftime('%Y-%m-%d %H:%M:%S'))



# kui script käivitub suvalisel hetkel, siis kõige odavama hetke määramiseks peab vaatama koos ajalooga
ee=download_prices(0,ohtuvenitus=1);
time.sleep(1)
hinnad2=sort_prices(ee)
chargelist=ehita_laadimislist(hinnad2,chargetime)
akuwh2=int(akuwh*(100-soc_minimum)/100) # kasutatav wh

avg_c=avg_s=0;
laadimine=0
for pair in (chargelist):
    tt=int(pair[0])
    print("Aeg: ",datetime.utcfromtimestamp(tt).strftime('%Y-%m-%d %H:%M:%S'),"hind ",round(pair[1],1),"senti; ", end = '')
    print("laadimistarve",(akuwh2 / chargetime/1000),"kWh, kokku",round((akuwh2 / chargetime/1000)*(pair[1]),1), "s" )
    #charge_price+=(akuwh2 / chargetime/1000)*(pair[1])  # tarve(kWh) * hind(senti)
    avg_c+=1
    avg_s+=pair[1]
    if tt>=tt_start and tt <= tt_end:
        print("Hetkel peaksime laadima")
        laadimine=1

keskmine_laadimishind=round(avg_s/avg_c,1)

#todo: keskmine laadimishind võiks võtta arvesse ka päeval päikesest laetud nullhinda.

inverttime=leia_inverttime();
print("Hetkel on veel lubatud invertida",inverttime,"tundi")
print("Keskmine laadimishind",keskmine_laadimishind,"senti") # see võib muutuda kui vahepeal laeti päikesest

tyhjendamine=0
avg_c=avg_s=0;

invertlist=hinnad2[::-1] # keerame listi tagurpidi, kõige kallimad ajad eespool
for pair in (invertlist):
    if max_inverttime<=0 or inverttime<=0: break # rohkem pole lubatud invertimisega tegeleda
    tt=int(pair[0])

    if tt>=tt_start:
        inverttime-=1; # tuleviku invertimised
    max_inverttime-=1 # kõik invertimiskorrad

    print("Aeg: ",datetime.utcfromtimestamp(int(pair[0])).strftime('%Y-%m-%d %H:%M:%S'),"hind ",round(pair[1],1),"senti; " , end = '')
    if pair[1]< keskmine_laadimishind+5:  # aku amort 4-5 senti kWh
        print(" ei ületa keskmist laadimishinda aku amordi võrra.")
        continue
    avg_c+=1
    avg_s+=pair[1]
    #print("energia",(keskmine_tunnitarve/1000),"kWh;  kokku",round((keskmine_tunnitarve/1000)*(pair[1]),1) , end = '')
    if tt < tt_start: #see tund oli juba ära
        print(" +")
    elif tt>=tt_start and tt <= tt_end:
        print(" <--")
    else:
        print("")
    if tt>=tt_start and tt <= tt_end:
        print("Hetkel peaksime tsüklisüsteemi juures tühjendama")
        tyhjendamine=1

current_soc_limit=loaddata2('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit')
soc_current=loaddata2('com.victronenergy.system','/Dc/Battery/Soc')
if avg_c>0:
    keskmine_tyhjendamishind=round(avg_s/avg_c,1)
else:
    keskmine_tyhjendamishind=0


solar_charge_estimate=next_solarpredict(solarpredict_url,1700) # omatarve 1700 on mu isikliku keskmise järgi
soc_maximum2=soc_maximum-min(int(round((100*solar_charge_estimate*1000/akuwh))), max_solar_soc_reserve);

#todo: kui soc pole X aega 100-ni jõudnud, siis soc_maximum2+=X*?

if soc_maximum2>98: # kui nii väike erinevus on, siis laadigu juba aku lõpuni täis
    soc_maximum2=100
if soc_maximum2< soc_minimum:
    soc_maximum2=soc_minimum

print ("Homse tootmise ennustus: ",solar_charge_estimate, "kWh, confi max soc:",soc_maximum, " seega võin laadida kuni: "+str(soc_maximum2)+"%");


if laadimine>0 and current_soc_limit < soc_maximum2:
    print("Seadmistame MinimumSocLimit = " , soc_maximum2)
    ret= setdata('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit', soc_maximum2)
elif laadimine>0:
    print("Kas on juba laadimine või oleme täis. Igaljuhul ei tee midagi")    
elif tyhjendamine>0 and current_soc_limit > soc_minimum:
    print("Seadmistame MinimumSocLimit = " , soc_minimum)
    ret= setdata('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit', soc_minimum)
elif tyhjendamine>0:
    print("Me kas juba tühjendame või oleme tühi. Igaljuhul ei muuda midagi")
elif tyhjendamine==0 and laadimine==0 and abs(current_soc_limit - soc_current)>1:
    # ei keela invertimist ega laadimist, samas laadimine ainult siis kui peaks tulema elektrit päikesest
    print("Seadmistame MinimumSocLimit = " , soc_current)        
    ret= setdata('com.victronenergy.settings','/Settings/CGwacs/BatteryLife/MinimumSocLimit', soc_current) 

charge_price=keskmine_laadimishind*akuwh2/1000
invert_price=keskmine_tyhjendamishind*akuwh2/1000
paevasaast=round(invert_price-charge_price)
print ("Laadimisega kulutan ", round(charge_price), "s, päeval kasutamata ",round(invert_price),"s, oletatav sääst",paevasaast,"senti")
#print("Oletatav sääst kuus",round((invert_price-charge_price)*31/100)," euri, aastas: ",round((invert_price-charge_price)*365/100))


