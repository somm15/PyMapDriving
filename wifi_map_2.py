
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

# Open the db
conn = sqlite3.connect('kismet.db')

c1 = conn.cursor()
devices=c1.execute("SELECT devmac,device FROM devices WHERE  min_lat<>0 AND min_lon<>0 AND type='Wi-Fi AP';") #devmac='C8:D3:A3:15:A7:7A' AND

ssids={}


max_lon=0
max_lat=0
min_lon=200000
min_lat=200000

for device in devices:
    jdevice=json.loads(device[1])
    #["kismet.device.base.location_cloud"]["kis.gps.rrd.samples_100"]
    ssid=jdevice["kismet.device.base.name"]
    mac=jdevice["kismet.device.base.macaddr"]
    if(not ssid in ssids):
        ssids[ssid]={}
        #print(ssid)
    if(not mac in ssids[ssid]):
        ssids[ssid][mac]=[]
        #print(mac)
    for measure in jdevice["kismet.device.base.location_cloud"]["kis.gps.rrd.samples_100"]:
        ssids[ssid][mac].append([measure["kismet.historic.location.lat"],measure["kismet.historic.location.lon"],measure["kismet.historic.location.signal"]])
        print(str(measure["kismet.historic.location.lat"])+"-"+str(measure["kismet.historic.location.lon"])+"-"+str(measure["kismet.historic.location.signal"]))
        max_lon=max(max_lon,measure["kismet.historic.location.lon"])
        min_lon=min(min_lon,measure["kismet.historic.location.lon"])
        max_lat=max(max_lat,measure["kismet.historic.location.lat"])
        min_lat=min(min_lat,measure["kismet.historic.location.lat"])

#print(ssids)
c_lat=(min_lat+max_lat)/2
c_lon=(max_lon+min_lon)/2

print(str(c_lat)+","+str(c_lon))

for ssid in ssids:
    map = folium.Map(location=[c_lat,c_lon],zoom_start=17)
    aps=folium.FeatureGroup("APs_"+ssid,show=False)
    ssidmap=folium.FeatureGroup("measures_"+ssid,show=False)
    heatmap=folium.FeatureGroup("heatmap_"+ssid,show=False)
    print("Starting net "+ssid+" with "+str(len(ssids[ssid]))+" APs")

    fp=[]
    for ap in ssids[ssid]:
        for p in ssids[ssid][ap]:
            fp.append([p[0],p[1],100+p[2]])

    print(fp)
    folium.plugins.HeatMap(fp,max_val=70).add_to(heatmap)


    nb_macs=len(ssids[ssid])
    i=0
    color_index=0
    for mac in ssids[ssid]:
        color=colors[color_index%3]
        print("Processing AP with mac "+mac +"("+ssid+") "+str(i)+"/"+str(nb_macs)+" APs")
        i=i+1
        print("AP has "+str(len(ssids[ssid][mac]))+ " measure points")
        measure_points=ssids[ssid][mac]
        best=None
        if(len(measure_points)>2):
            for n in np.arange(2.0, 5.0, 0.1):
                frame=0.05
                res_0 = least_squares(locate_ap_fixed, [c_lat,c_lon],bounds=[[min_lat-frame, min_lon-frame],[max_lat+frame, max_lon+frame]],args=([measure_points]),kwargs={"n_fixed":n})

                sum_error=res_0.fun
                #for temp in res_0.fun:
                #    sum_error+=temp

                if(best==None  or sum_error<best[3]):
                    best=[res_0.x[0], res_0.x[1],n,sum_error]

            print("Best solution 0 is "+str(best))
            folium.Marker([best[0], best[1]], popup=str(ssid)+"/"+str(mac)+"\n Error "+str(res_0.fun), tooltip=str(ssid)+"/"+str(mac),icon=folium.Icon(color=color,icon='fa-wifi',prefix='fa')).add_to(aps)

        #print("Using n "+str(best[2]))

        for measure in measure_points:
            RSSI=measure[2]
            folium.Marker([measure[0], measure[1]], popup=str(ssid), tooltip="SSID: "+ssid +" Mac: "+mac,icon=folium.Icon(color=color,prefix='fa',icon='fa-signal')).add_to(ssidmap)
            if(best != None):
                n=best[2]
                ptx=18.5
                d = 10.0**((ptx-RSSI)/(10*n))
                print("Circle with radius "+str(d))
                folium.CircleMarker(location=[measure[0], measure[1]],radius=d,popup=str(mac)+" radius is "+str(d),color=color,fill=False,fill_color=color).add_to(ssidmap)
        color_index=color_index+1
    map.add_child(aps)
    map.add_child(heatmap)
    map.add_child(ssidmap)
    folium.LayerControl(collapsed=False).add_to(map)
    map.save('result_'+ssid+'.html')
