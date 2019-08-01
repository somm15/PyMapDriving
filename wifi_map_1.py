
import sqlite3
import folium
from folium import plugins
from scipy.optimize import least_squares
import numpy as np
import math
from math import sin, cos, sqrt, atan2, radians

def locate_ap(p1,measure_point):
    error=0
    for point in measure_point:
        RSSI=point[2]
        ptx=18.5 # emission power
        n=p1[2] # n value
        d = 10.0**((ptx-RSSI)/(10*n))

        R = 6373.0
        p2 = [point[0],point[1]]
        lat1 = radians(p1[0])
        lon1 = radians(p1[1])
        lat2 = radians(p2[0])
        lon2 = radians(p2[1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c * 1000
        error=error+abs(distance-d)
    #print(str(p1)+"-->"+str(error))
    return error

def locate_ap_fixed(p1,measure_point,n_fixed):
    error=0
    for point in measure_point:
        RSSI=point[2]
        ptx=18.5 # emission power
        n=n_fixed
        d = 10.0**((ptx-RSSI)/(10*n))
        R = 6373.0
        p2 = [point[0],point[1]]
        lat1 = radians(p1[0])
        lon1 = radians(p1[1])
        lat2 = radians(p2[0])
        lon2 = radians(p2[1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c * 1000
        error=error+abs(distance-d)
    #print(str(p1)+"-->"+str(error))
    return error

# Create the map
map_all = folium.Map(location=[47.684198, 8.729031],zoom_start=17)
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
conn = sqlite3.connect('recon_analysis.db')

c1 = conn.cursor()
measures=c1.execute("SELECT bssid,ssid,lat,long,signal FROM aps WHERE lat IS NOT NULL AND lat!=''")
ssids={}

for measure in measures:
    if(not measure[1] in ssids):
        ssids[measure[1]]={}
    ssid=ssids[measure[1]]
    if(not measure[0] in ssid):
        ssids[measure[1]][measure[0]]=[]
    ssids[measure[1]][measure[0]].append([measure[2],measure[3],measure[4]])
print(ssids)

map = folium.Map(location=[47.684198, 8.729031],zoom_start=17)

for ssid in ssids:
    m=folium.FeatureGroup(ssid,show=False)
    h=folium.FeatureGroup(ssid+"_heat",show=False)

    print("Starting net "+ssid+" with "+str(len(ssids[ssid]))+" APs")

    fp=[]
    for ap in ssids[ssid]:
        for p in ssids[ssid][ap]:
            fp.append([p[0],p[1],100+p[2]])
    print(fp)
    folium.plugins.HeatMap(fp,max_val=70,radius=100,overlay=True,control=True,name=ssid+"_heat").add_to(h)
    map.add_child(h)
    aps=folium.FeatureGroup(ssid+"_AP",show=False)
    map.add_child(aps)

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
                frame=0.02
                res_0 = least_squares(locate_ap_fixed, [47.684603, 8.727743],bounds=[[47.679461-frame, 8.719129-frame],[47.690208+frame, 8.741397+frame]],args=([measure_points]),kwargs={"n_fixed":n})
                #print("First estimate "+str(res_0.x)+" with error "+str(res_0.fun)+" for n = "+str(n))
                if(best==None  or res_0.fun<best[3]):
                    best=[res_0.x[0], res_0.x[1],n,res_0.fun]
            print("Best solution 0 is "+str(best))
            folium.Marker([best[0], best[1]], popup=str(ssid)+"/"+str(mac)+"\n Error "+str(res_0.fun), tooltip=str(ssid)+"/"+str(mac),icon=folium.Icon(color=color,icon='fa-wifi',prefix='fa')).add_to(m)
            folium.Marker([best[0], best[1]], popup=str(ssid)+"/"+str(mac)+"\n Error "+str(res_0.fun), tooltip=str(ssid)+"/"+str(mac),icon=folium.Icon(color=color,icon='fa-wifi',prefix='fa')).add_to(aps)


        for measure in measure_points:
            RSSI=measure[2]
            folium.Marker([measure[0], measure[1]], popup=str(ssid), tooltip="SSID: "+ssid +" Mac: "+mac,icon=folium.Icon(color=color,prefix='fa',icon='fa-signal')).add_to(m)
            if(best != None):
                ptx=18.5 # emission power
                n=best[2] # REPLOIACE TODO
                d = 10.0**((ptx-RSSI)/(10*n))
                folium.CircleMarker(location=[measure[0], measure[1]],radius=d,popup=str(mac)+" radius is "+str(d),color=color,fill=False,fill_color=color).add_to(m)
        color_index=color_index+1
    #folium.LayerControl(collapsed=True).add_to(m)
    map.add_child(m)
folium.LayerControl(collapsed=False).add_to(map)
map.save('result.html')
