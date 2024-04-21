# Automated Earthquake Identification And Notification Systems
This repository is for my dissertation project of Durham MDS. 
## use interactiveMain.ipynb for examples of current progress.


This flowchart showing below would reflect my current design and progress.
<img src="Flowchart.drawio.png" width="600"><br />


# Progress Log
### 2024-04-18 <br />
Built a functional DataDownload.py for downloading seismic data from specified station and date.<br />
Moving on to seismic data preprocessing in DataProcessing.py. <br />
Doing more background reading and improving overall code design.<br />
<br />
### 2024-04-19<b/> <br />
Still working on preprocessing and denoising. <br />
Looking for best parameters to produce clean seismic streams.<br />
Starting to build EventIdentification.py for earthquake identification using STA/LTA method from processed seismic data.<br />
Added an interactive Jupyter notebook version of main.py for testing and playing around.<br />

### 2024-04-21<b/> <br />
FDSNWS service still unavailable. Used https://data.raspberryshake.org for data. <br />
Improved codes for outliers/ extreme values removal.  <br />
Working on implementing a denoising algorithm. <br />
Added a util.py for utility functions like getting lat and long of a given station.  <br />
