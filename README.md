# Automated Earthquake Identification And Notification Systems
This repository is for my dissertation project of Durham MDS. <br />

## Usage
Run interactiveMain.ipynb for examples of latest progress.<br />

## Flowchart of Project/ Code Design
This reflect my current design and progress and will be updated constantly.
<img src="Project.drawio.png" width="820"><br />


## Progress Log
### 2024-04-18 <br />
Built a functional DataDownload.py for downloading seismic data from specified station and date.<br />
Moving on to seismic data preprocessing in DataProcessing.py. <br />
Doing more background reading and improving overall code design.<br />

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

### 2024-04-23<b/> <br />
Added a predict_arrivals() to predict arrival times of earthquakes identified from daily stream. <br />
Planning to implement a module in the future to analysis noise pattern and output produce more "tailored" parameters for denoising. <br />
Working on finding the best parameters for STA/ LTA window and threshold to better identify earthquake events. <br />

### 2024-04-25<b/> <br />
Made major changes to overall designs: <br />
1. Will attempt to identify earthquakes within predicted time windows first instead of identifying events from entire day's stream.<br />
2. A DataFrame will be used to store all earthquake events to maintain consistency of formatting.<br />
3. Combination of "catalogued" and "detected" column values are used to represent the state of the event.<br />
4. Refer to flowchart for more details of code design.<br />

Download function now download from 23:00 T-1 to 01:00 T+1, while catalogue returns events from 23:30 T-1 to 00:30 T+1 to avoid predicted time windows falling on empty stream. <br />

Need to find a way to make sure event identified within time window is indeed the one we are looking for.<br />
Still working on finding best parameters for preprocessing/denosing.<br />

### 2024-04-28<b/> <br />
Improved overall code logic.  <br />
Redesigned flowchart for better representation of project design. Seprated code module design from flowchart.<br />
Added "detected_start" column to DataFrame for storing observed starting time for catalogued earthquakes. <br />
Added functions to plot predicted times and identified times on the waves for better visualization.  Example: <br />
<img src="misc/example_plot.png" width="650"><br />
Added a basic function matching detected events with catalogued earthquakes by comparing times.  <br />
Working on finding best parameters for STA/LTA and preprocessing/denosing.<br />
Planning on building a real-time script to report latest events by continously monitoring a catalogue. This will generate emails for individual events captured on local stations<br />

### 2024-04-29<b/> <br />
Changed back to the more efficient way of analyzing the daily stream as whole.<br />
The program now generates two dataframes: one for catalogued events and another for detected events.Then it performs a matching and merging process on these events.<br /> 
Might try something like iterating over a range parameters to find the best parameter combinations to maximize the chance of detecting the events listed in the catalogue.<br /> 

### 2024-04-30<b/> <br />
Major changes: <br /> 
Implemented pre-trained deep learning models from [SeisBench](https://github.com/seisbench/seisbench) for denosing and event detection/ phase picker. Seems to work quite well (and fast). <br /> 
Pre-trained models could identify wave phases and produce confidence scores for the predictions, so we have a more precise way of match and merging the events.<br /> 
Other changes: <br /> 
Now the codes request events from multiple catalogues in case service denied/ down. If all failed, it will sleep for 60s and retry. <br /> 

### 2024-05-01<b/> <br />
Tried different pre-trained models for phase picking. <br /> 
Optimized existig codes for post-processing.  <br /> 
Next steps: <br /> 
Add some codes save catalogues to file and add check if catalgue for a date has already been requested before before requesting.  <br /> 
Save each day's final dataframe to csv files and generate email contents based on it.<br /> 

### 2024-05-02<b/> <br />
Added GPU support. If CUDA is available, models will run on GPU for acceleration.  <br /> 
Added probability plotting of picked phases when visualizing the matched event. Example:  <br /> 
<img src="misc/0502-1.png" width="650"><br />
Improved existing codes. <br />


