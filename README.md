# Automated Earthquake Identification And Notification Systems
This repository is for my dissertation project of Durham MDS. <br />

## Demo Usage
See main.ipynb and for report_generation.ipynb for latest progress.<br />

## Flowchart of Project/ Code Design
This reflect my current design and progress and will be updated constantly.
<img src="Project.drawio.png" width="820"><br />


## Progress Log
### 2024-04-18 <br />
1. Built a functional DataDownload.py for downloading seismic data from specified station and date.<br />
2. Moving on to seismic data preprocessing in DataProcessing.py. <br />
3. Doing more background reading and improving overall code design.<br />

### 2024-04-19<b/> <br />
1. Still working on preprocessing and denoising. <br />
2. Looking for best parameters to produce clean seismic streams.<br />
3. Starting to build EventIdentification.py for earthquake identification using STA/LTA method from processed seismic data.<br />
4. Added an interactive Jupyter notebook version of main.py for testing and playing around.<br />

### 2024-04-21<b/> <br />
1. FDSNWS service still unavailable. Used https://data.raspberryshake.org for data. <br />
2. Improved codes for outliers/ extreme values removal.  <br />
3. Working on implementing a denoising algorithm. <br />
4. Added a util.py for utility functions like getting lat and long of a given station.  <br />

### 2024-04-23<b/> <br />
1. Added a predict_arrivals() to predict arrival times of earthquakes identified from daily stream. <br />
2. Planning to implement a module in the future to analysis noise pattern and output produce more "tailored" parameters for denoising. <br />
3. Working on finding the best parameters for STA/ LTA window and threshold to better identify earthquake events. <br />

### 2024-04-25<b/> <br />
Made major changes to overall designs: <br />
1. Will attempt to identify earthquakes within predicted time windows first instead of identifying events from entire day's stream.<br />
2. A DataFrame will be used to store all earthquake events to maintain consistency of formatting.<br />
3. Combination of "catalogued" and "detected" column values are used to represent the state of the event.<br />
4. Refer to flowchart for more details of code design.<br />

### 2024-04-26<b/> <br />
1. Download function now download from 23:00 T-1 to 01:00 T+1, while catalogue returns events from 23:30 T-1 to 00:30 T+1 to avoid predicted time windows falling on empty stream. <br />
2. Need to find a way to make sure event identified within time window is indeed the one we are looking for.<br />
3. Still working on finding best parameters for preprocessing/denosing.<br />

### 2024-04-28<b/> <br />
1. Improved overall code logic.  <br />
2. Redesigned flowchart for better representation of project design. Seprated code module design from flowchart.<br />
3. Added "detected_start" column to DataFrame for storing observed starting time for catalogued earthquakes. <br />
4. Added functions to plot predicted times and identified times on the waves for better visualization.  Example: <br />
<img src="misc/example_plot.png" width="550"><br />
5. Added a basic function matching detected events with catalogued earthquakes by comparing times.  <br />
6. Working on finding best parameters for STA/LTA and preprocessing/denosing.<br />
7. Planning on building a real-time script to report latest events by continously monitoring a catalogue. This will generate emails for individual events captured on local stations<br />

### 2024-04-29<b/> <br />
1. Changed back to the more efficient way of analyzing the daily stream as whole.<br />
2. The program now generates two dataframes: one for catalogued events and another for detected events.Then it performs a matching and merging process on these events.<br /> 
3. Might try something like iterating over a range parameters to find the best parameter combinations to maximize the chance of detecting the events listed in the catalogue.<br /> 

### 2024-04-30<b/> <br />
Major changes: <br /> 
1. Implemented pre-trained deep learning models from [SeisBench](https://github.com/seisbench/seisbench) for denosing and event detection/ phase picker. Seems to work quite well (and fast). <br /> 
2. Pre-trained models could identify wave phases and produce confidence scores for the predictions, so we have a more precise way of match and merging the events.<br /> 
Other changes: <br /> 
3. Now the codes request events from multiple catalogues in case service denied/ down. If all failed, it will sleep for 60s and retry. <br /> 

### 2024-05-01<b/> <br />
1. Tried different pre-trained models for phase picking. <br /> 
2. Optimized existig codes for post-processing.  <br /> 

### 2024-05-02<b/> <br />
1. Improved existing codes and fixed some issues. <br />
2. Added GPU support. If CUDA is available, models will run on GPU for acceleration.  <br /> 
3. Catalogues requested are saved to QuakeXML file. It will check if it already exists before requesting.<br /> 
4. Added probability plotting of picked phases when visualizing the matched event.<br /> 
   Example:  <br /> 
<img src="misc/0502-1.png" width="550"><br />

### 2024-05-04<b/> <br />
1. DataFrame now contains unique event ID, depth, epicentral distance for catalogued events. <br /> 
2. Added plot function for showing catalogued events and station on globe map. Has the option to toggle map filling. <br />
   Examples of map filling on/off: <br />
<img src="misc/0504-1.png" width="450"><br />
<img src="misc/0504-2.png" width="450"><br />
3. Functions for downloading mseed files and catalogues now have the option to download again and overwrite already existing files. <br /> 
4. Optimized a lot of existing codes. Deleted unused and old functions. <br />

### 2024-05-05<b/> <br />
1. Now all processed streams, phase picking predictions/ annotations and results will be saved to files.<br />
2. The files saved will used for generating contents for the email notifications or build a database in the future.  <br />
3. Added contentGeneration.ipynb for testing building contents for report/email.<br />
See this [PDF](generated/ExampleEmailContent.pdf) for example for email content built using HTML.<br />

Next steps: Improve exceptions catching and file management.<br />

### 2024-05-06<b/> <br />
1. Kept working on codes for building HTML. <br />
2. Added report_generation.ipynb to demonstrate content generation using files produced from main.ipynb. See Noteebook and this [PDF](generated/ExampleEmailContent.pdf) for latest example.<br />
2. Worked on tweaking parameters for requesting catalogues to maximize chance of matching events.<br />
3. Fixed a number of small bugs. <br />
4. Updated flowchart to reflex latest code design. <br />

### 2024-05-07<b/> <br />
Just found out that P waves are usually much more easier to be detected than S waves with higher accuracy and lower prediction time error. Added feature to set different threshold and tolerance values for P and S when filtering picking confidence and matching events. <br />
Added spectrogram plotting for the matched events. Now the report shows waveform(with predicted and picked time marked) + prediction confidence(probability) + spectrogram. Example:  <br />  
<img src="misc/0507.png" width="550"><br />
Added function for email message preparation, which prepare emails content by embedding images as MIMEImage objects to message. <br />
Added function for sending the emails to designated recipient using SMTP. <br />
Email sending function is working but Outlook and Gmail do not render it correctly for security reasons. Tested in other email clients and works as expected.<br />

### 2024-05-08<b/> <br />
1. Utilized a new GitHub repo dedicated for image hosting to HTML with embedded images not rendering correctly.<br />
2. Improved catalogue map plot: Now detected and undetected events are shown in different shapes. Legend also shows numbers for each.<br />
3. Introducing a "simplified" mode when generating report. Hiding a few technical details. <br />
4. Streamlined codes for reading previously produced files and generating reports. <br />
5. Added columns for calculated time errors between predicted and detected values in DataFrame after match-n-merge. <br />






