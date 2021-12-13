# -*- coding: utf-8 -*
from __future__ import print_function
from __future__ import division
import os

# sinna kataloogi korjame logi, cache jmt. jooksva tööinfo. Oleks mõistlik internal flashi asemel panna mälukaardile
workdir= "/run/media/mmcblk0p1/ess_data"

# winni masinas mugav näiteks nii kasutada:
#workdir= os.path.dirname(os.path.realpath(__file__))+os.path.sep+".."+os.path.sep+"victron_ess_temp"

# personaalne url, millelt homset päikesennustust alla laadida (uuri solcast.com.au)
solarpredict_url=""

chargetime=4 # mitu tundi lubame soodusajal laadida
max_inverttime=20 # mitu tundi max inverteril on lubatud. Võib olla ka 24. Rohkem testimise jaoks see muutuja


soc_minimum= 20 # kui tühjaks lubame aku lasta
soc_maximum=100 # kui palju maksimaalselt võrgust laeme

akuwh=14000   # aku kogumahtuvus Wh-s
