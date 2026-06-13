# -*- coding: utf-8 -*-

'''
Plotting code for the altimeter and pollution sensor data

Compiling seperate scripts for plotting the data from the .csv files written by the data collection scripts

This code is designed to be run on a computer/laptop not the pi itself as it uses larger libraries like pandas
'''

# Imports ---------
import pandas as pd      
import numpy as np
import matplotlib.pyplot as plt


#Reading and Plotting the altimeter data --------------------------
df = pd.read_csv('flight_data.csv') # read the dataframe  MAKESURE IT IS CALLED THIS  ('flight_data')
df = df.dropna() # drops NaN rows with bad data that may mess with results
df['Time(s)'] = df['Time(ms)'] / 1000  # convert the time in ms to s
print("Column titles:", df.columns)  # to check column names are what we have them used in the script as
time = df['Time(s)']
altitude = df['Altitude(m)']

plt.figure(figsize = (10,6))

plt.plot(time, altitude, label = 'Flight Path')

apogee = altitude.max()
max_time = time[altitude.idxmax()]
plt.scatter(max_time, apogee, color= 'r', zorder = 5, label = 'Apogee')
print('Apogee found at:', apogee, 'm')
apo_feet = apogee * 3.281
print(f'In feet the apogee is {apo_feet:.2f} ft, with a percentage difference of: {((1500 - apo_feet)/1500)*100:.2f} %.') 

plt.xlabel("Time since launch (s)")
plt.ylabel("Altitude (m)")
plt.title("Rocket Altitude vs Time")
plt.grid(True)
plt.legend()

plt.savefig("Altitude_vs_Time.png", dpi = 300)   # save as a .png and close it so the rest of the code can run -> done for all the others too
plt.close()




# Reading and plotting 4 graphs from the pollution sensor data --------------

#df = pd.read_csv('flight_data.csv') # read the dataframe MAKESURE IT IS CALLED THIS  ('pollution_sensor_data')
#df = df.dropna() # drops NaN rows with bad data that may mess with results
#print("Polllution Sensor column titles:", df.columns)  # to check column names are what we have them used in the script as


# --------- Graph 1: PM
#
df.plot(x = "Time(s)", y = ["PM1.0", "PM2.5", "PM10.0"], figsize = (10,8), title = "Particulate Matter vs Time", grid = True, legend = True, xlabel = "Time from Launch", ylabel = "Concentration of Particulate Matter")
plt.savefig("PM_vs_time.png", dpi = 300)
plt.close()
# "PM1.0", 

# --------- Graph 2: VOC/NOx Indices
#
df.plot(x = "Time(s)", y = ["VOC_Index", "NOX_Index"], figsize = (10,8), title = "Index of Organic Compounds vs Time", grid = True, legend = True, xlabel = "Time from Launch", ylabel = "VOC/NOx Index")
plt.savefig("vox_nox_vs_time.png", dpi = 300)
plt.close()

df.plot(x = "Time(s)", y = ["VOC_Index"], figsize = (10,8), title = "Index of Organic Compounds vs Time", grid = True, legend = True, xlabel = "Time from Launch", ylabel = "VOC Index")
plt.savefig("vox_vs_time.png", dpi = 300)
plt.close()

df.plot(x = "Time(s)", y = ["NOX_Index"], figsize = (10,8), title = "Index of Organic Compounds vs Time", grid = True, legend = True, xlabel = "Time from Launch", ylabel = "NOx Index")
plt.savefig("nox_vs_time.png", dpi = 300)
plt.close()




#in order to make the graph more useful and readable, will plot the ascent and descent separately (diff colours?)
altitude = df['Altitude(m)'] # from altimeter - same as above
apogee = altitude.max()    # find the max altitude - same as above
apogee_index = altitude.idxmax()


ascent = df.loc[:apogee_index]
descent = df.loc[apogee_index:]


# --------- Graph 3: Altitude vs PM
fig, ax = plt.subplots(figsize = (10,8))

ascent.plot.scatter(x = "Altitude(m)", y = "PM1.0", color = "darkblue", alpha = 0.5, label = "Ascent PM1.0", ax = ax)
ascent.plot.scatter(x = "Altitude(m)", y = "PM2.5", color = "blueviolet", alpha = 0.5, label = "Ascent PM2.5", ax = ax)
ascent.plot.scatter(x = "Altitude(m)", y = "PM10.0", color = "dodgerblue", alpha = 0.5, label = "Ascent PM10.0", ax = ax)

descent.plot.scatter(x = "Altitude(m)", y = "PM1.0", color = "darkred", alpha = 0.5, label = "Descent PM1.0", ax = ax)
descent.plot.scatter(x = "Altitude(m)", y = "PM2.5", color = "red", alpha = 0.5, label = "Descent PM2.5", ax = ax)
descent.plot.scatter(x = "Altitude(m)", y = "PM10.0", color = "tomato", alpha = 0.5, label = "Descent PM10.0", ax = ax)

plt.ylabel("Concentration of Particulate Matter")
plt.xlabel("Altitude (m)")
plt.title("Particulate Matter vs Altitude Graph")
plt.grid(True)
plt.legend()

#df.plot.scatter(x = altitude, y = ["PM1.0", "PM2.5", "PM10.0"], figsize = (10,8), alpha = 0.5, title = "Particulate Matter vs Altitude", grid = True, legend = True, xlabel = "Altitude", ylabel = "Concentration of Particulate Matter")
plt.savefig("PM_vs_altitude.png", dpi = 300)
plt.close()



# --------- Graph 4: Altitude vs VOC/NOx Indices

#VOX Graph
fig, ax = plt.subplots(figsize = (10,8))

ascent.plot.scatter(x = "Altitude(m)", y = "VOC_Index", color = "darkred", alpha = 0.5, label = "Ascent VOC", ax = ax)
descent.plot.scatter(x = "Altitude(m)", y = "VOC_Index", color = "orangered", alpha = 0.5, label = "Descent VOC", ax = ax)

plt.ylabel("VOC Index")
plt.xlabel("Altitude (m)")
plt.title("Index of Organic Compounds vs Altitude")
plt.grid(True)
plt.legend()

#df.plot.scatter(x = altitude, y = ["VOC_Index", "NOX_Index"], figsize = (10,8), alpha = 0.5, title = "Index of Organic Compounds vs Altitude", grid = True, legend = True, xlabel = "Altitude", ylabel = "VOC/NOx Index")
plt.savefig("vox_vs_altitude.png", dpi = 300)
plt.close()


# NOX Graph
fig, ax = plt.subplots(figsize = (10,8))

ascent.plot.scatter(x = "Altitude(m)", y = "NOX_Index", color = "mediumblue", alpha = 0.5, label = "Ascent NOx", ax = ax)
descent.plot.scatter(x = "Altitude(m)", y = "NOX_Index", color = "darkviolet", alpha = 0.5, label = "Descent NOx", ax = ax)

plt.ylabel("NOx Index")
plt.xlabel("Altitude (m)")
plt.title("Index of Organic Compounds vs Altitude")
plt.grid(True)
plt.legend()

plt.savefig("nox_vs_altitude.png", dpi = 300)
plt.close()





# Result should be 8 graphs saved as .png images in the same folder as the code
