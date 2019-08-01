
import sqlite3
import folium
from folium import plugins
from scipy.optimize import least_squares
import scipy
import numpy as np
import math
from math import sin, cos, sqrt, atan2, radians
import json
from vincenty import vincenty
from haversine import haversine
import gpxpy
from datetime import datetime
from datetime import timezone

max_lon=0
max_lat=0
min_lon=200000
min_lat=200000

def locate_ap_fixed2(p1,measure_points):
    return locate_ap_fixed(p1,measure_points,4.9)

def locate_ap_fixed(p1,measure_points,n_fixed):
    error=0
    errors=[]
    for point in measure_points:
        RSSI=point[2]
        ptx=18.5 # emission power
        n=n_fixed
        d = 10.0**((ptx-RSSI)/(10*n))
        p2 = [point[0],point[1]]
        distance = vincenty(p1,p2)*1000
        p_error=abs(distance-d)
        #print("Theoritical: "+str(d)+" Computed: "+str(distance)+" Error: "+str(p_error))
        error+=p_error
        errors.append(p_error)
    #return (error/len(measure_points))
    return error

# Create the map
colors = [
    'red',
    'blue',
    'gray',
    'darkred',
    'lightred',
    'orange',
    'beige',
    'green',
    'darkgreen',
    'lightgreen',
    'darkblue',
    'lightblue',
    'purple',
    'darkpurple',
    'pink',
    'cadetblue',
    'lightgray',
    'black'
]


points=[]
gpx = gpxpy.parse(open("wardriving.gpx"))
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            points.append(point)
            #datetime_object = datetime.strptime(point.time, '%Y-%m-%d %H:%M:%S')
            #print(datetime_object)

ssids={}

# Open the db
conn = sqlite3.connect('kismet.db')
c1 = conn.cursor()
devices=c1.execute("SELECT devmac,device FROM devices WHERE type='Wi-Fi AP';") #devmac='C8:D3:A3:15:A7:7A' AND
mac_to_ssid={}

for device in devices:
    jdevice=json.loads(device[1])
    #["kismet.device.base.location_cloud"]["kis.gps.rrd.samples_100"]
    #ssid=jdevice["kismet.device.base.name"]
    mac=jdevice["kismet.device.base.macaddr"]
    ssid_map=jdevice["dot11.device"]["dot11.device.advertised_ssid_map"]
    for item in ssid_map:
        ssid=ssid_map[item]["dot11.advertisedssid.ssid"]
        if(not ssid in ssids):
            ssids[ssid]={}
            #print(ssid)
        if(not mac in ssids[ssid]):
            ssids[ssid][mac]=[]
        mac_to_ssid[mac]=ssid

print("Number of ssids: "+str(len(ssids)))


c2 = conn.cursor()
packets = c2.execute("SELECT ts_sec,sourcemac,destmac,signal FROM packets WHERE NOT (sourcemac ='00:00:00:00:00:00' AND destmac ='00:00:00:00:00:00');")

for packet in packets:
    time=datetime.fromtimestamp(packet[0],tz=timezone.utc)
    sourcemac=packet[1]
    destmac=packet[2]
    signal=packet[3]
    for point in points:
        if time <= point.time:
            #print("First match")
            #print(str(point.time) +" "+str(time))
            max_lon=max(max_lon,point.longitude)
            min_lon=min(min_lon,point.longitude)
            max_lat=max(max_lat,point.latitude)
            min_lat=min(min_lat,point.latitude)
            if(sourcemac in mac_to_ssid):
                ssid=mac_to_ssid[sourcemac]
                ssids[ssid][sourcemac].append([point.latitude,point.longitude,signal])
            if(destmac in mac_to_ssid):
                ssid=mac_to_ssid[destmac]
                p=[point.latitude,point.longitude,signal]
                if not p in ssids[ssid][destmac]:
                    ssids[ssid][destmac].append(p)
            break

#print(ssids)
c_lat=51.510417
c_lon=-0.080348

print(str(c_lat)+","+str(c_lon))


for ssid in ssids:
    fp=[]
    for ap in ssids[ssid]:
        for p in ssids[ssid][ap]:
            fp.append([p[0],p[1],100+p[2]])
    if len(fp) > 3:
        map = folium.Map(location=[c_lat,c_lon],zoom_start=17)
        heatmap=folium.FeatureGroup("heatmap_"+ssid,show=True)
        folium.plugins.HeatMap(fp,max_val=70).add_to(heatmap)
        map.add_child(heatmap)
        folium.LayerControl(collapsed=False).add_to(map)
        map.save("result-"+str(ssid)+'.html')
