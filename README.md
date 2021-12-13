# Taust

Scriptike on kirjutatud oma tarbeks, seega võib sisaldada veidraid konstante jmt. staatilisi jupikesi, mis on seotud minu koduse süsteemiga

# Kasutus

Seadista conf failis: victron_nps_localconf.py

Käivita scripti "victron_nps_ess.py" kas crontabiga iga X minuti järel või terminalis näiteks "watch -n 200 python victron_nps_ess.py"

Minimaalselt vaja käivitada kord tunnis (näiteks esimesel minutil), et tehtaks tunni kohta õige otsus, samas kui koormus muutub, võib käivitada kasvõi iga 5 min järel.


# Toimimine:

Valitakse välja kõige soodsamad tunnid aku laadimiseks

Kõige kallimatel tundidel kasutatakse akut ja elektrit võrgust ei võeta

Vastavalt aku laetusele lisatakse jooksvalt tunde (päevane päikese laadimine) või visatakse mõni tund välja (suurenev koormus)


# todo:
Arvestada solarpredictionit jätmaks akusse päevase laadimise jaoks ruumi

Arvestada ajalugu, et aku pidevalt SoC alumises otsas poleks (umbes nagu victron battery optimizer)

Logida tarbimist hindamaks paremini keskmist (praegu kasutatakse viimase mõõtmise hetkevõimsust)

# tulemus:
Tarbimine võrgust: ![Elektrikastus võrgust](power_from_grid.PNG)
