from tkinter import filedialog
from tkinter import *
from tkinter import ttk
import pymysql
from tkinter import messagebox


class loadDataGUI():
    # establish db connection to be used
    connection = pymysql.connect(host='localhost',
                                 user='root',
                                 password='pswd',
                                 db='empaticareader')

    cursor = connection.cursor()

    def __init__(self):
        self.datawin = Tk()

        self.datawin.geometry('175x200+800+200')

        self.datawin.title('Empatica Reader')

        self.infolbl = ttk.Label(self.datawin, wraplength = 150, text = 'Select the name of the folder downloaded from the website')\
            .place(relx = .5, rely = .1, anchor = 'n')

        self.loadButton = ttk.Button(self.datawin, text='Choose folder for upload', command=self.open) \
            .place(relx=.5, rely=.5, anchor="center")

        self.fin = ttk.Button(self.datawin, text='done', command=self.close) \
            .place(relx=.5, rely=.8, anchor="center")

        self.datawin.mainloop()

    def close(self):
        self.datawin.destroy()

    def open(self):
        self.path = filedialog.askdirectory()
        self.activity = open(self.path + "/ACC.csv")
        self.heartRate = open(self.path + "/HR.csv")
        self.arousal = open(self.path + "/EDA.csv")

        self.hrarr = self.heartRate.read().split("\n")
        self.accarr = self.activity.read().split("\n")
        self.arousalarr = self.arousal.read().split("\n")

        # to put timestamp to next lowest hour
        stime = int(float(self.hrarr[0])) % 3600
        stime = int(float(self.hrarr[0])) - stime


        # fills any missing dates with 0
        self.fill(self.hrarr[0])

        etime = len(self.hrarr) // 3600
        etime = etime*3600 + stime                  #number of hours in file

        while stime <= etime:
            try:
                exe = 'INSERT INTO data (date) VALUES ('+str(stime)+');'
                self.cursor.execute(exe)
                self.connection.commit()
            except:
                self.connection.rollback()

            stime += 3600

        # call the methods to compile the data from the files
        self.dbavger(self.hrarr)
        self.dbavger(self.arousalarr)
        self.accavg(self.accarr)
        messagebox.showinfo(title = 'Confirm', message = 'Uploaded!')

    # method to fill missing rows of db
    def fill(self, dat):
        # find start of file to know how much to fill
        time = int(float(dat)) % 3600
        time = int(float(dat)) - time + 3600

        # pull largest and thus most recent date from db
        self.cursor.execute('SELECT MAX(date) FROM Data')
        last = self.cursor.fetchone()
        num = int(last[0])

        i = 1
        # fill the days with no data with 0's
        while (num < time):
            try:
                stat = 'INSERT into Data (date, ACC, HR, EDA) VALUES(' + str(num) + ', 0,0,0)'
                self.cursor.execute(stat)
                self.connection.commit()
            except:
                self.connection.rollback()
            num = num + 3600

    # commits data to data base
    def commitdb(self, ar, st):
        i = 0

        # to put timestamp to next lowest hour
        time = int(float(self.hrarr[0])) % 3600
        time = int(float(self.hrarr[0])) - time + 3600

        # inserts all values from array to database
        while (i < len(ar)):
            try:
                com = 'UPDATE data SET ' + st + '=' + str(ar[i]) + ' WHERE date = '+str(time)+';'
                self.cursor.execute(com)
                self.connection.commit()
            except:
                self.connection.rollback()
            i = i + 1
            time = time + 3600

    def dbavger(self, ary):
        # first we pull the timestamp and smaple rate from file
        timestamp = int(float(ary[0]) % 3600)
        sampleRate = int(float(ary[1]))
        arrayIndex = 0
        # then we cut partial hours
        if (timestamp > 0):
            arrayIndex = timestamp * sampleRate
        # set timestamp to first full hour of data
        timestamp = float(ary[0])+(timestamp-3600)
        counter = 0  # will hold measurements per hour, used in inner loop
        returnVal = []
        type = ""
        sum = 0
        divisor = 0  # will hold duplicate of counter, not changed in loop
        average = 0
        hours = 0

        # see if file is for HR or EDA
        if (sampleRate == 1):
            type = "HR"
            counter = 360
            divisor = 360
        elif (sampleRate == 4):
            type = "EDA"
            counter = 1440
            divisor = 1440

        # find the length of the file so we know when to stop, cutting any partial hours
        end = len(ary) - arrayIndex
        leftOver = end % divisor
        end = end - leftOver
        leveler = (end - arrayIndex) % 10
        end = end - leveler

        # nested loop to calculate averages for the hours in the file, outer is for whole file, inner is for each hour
        # (end - divisor *20) this makes sure the last time this loop executes is on the last hour
        while (arrayIndex <= (end - divisor * 10)):
            sum = 0
            while (counter > 0):
                sum += float(ary[arrayIndex])  # array index increments by ten to reduce number of calculations
                arrayIndex += 10
                counter -= 1
            average = sum / divisor
            returnVal.append(average)  # store the average for this hour in the return array
            counter = divisor
            hours += 1

        # commit list to db
        self.commitdb(returnVal, type)

    # special case averager for the ACC file, since it uses three columns and 3D measurements
    def accavg(self, acclist):
        # first we pull the timestamp and sample rate from file
        timerow = acclist[0].split(',')
        timestamp = int(float(timerow[0]) % 3600)
        samplerow = acclist[1].split(',')
        sampleRate = int(float(samplerow[1]))
        arrayIndex = 0
        # then we cut partial hours off the front
        if (timestamp > 0):
            arrayIndex = timestamp * sampleRate
        # set timestamp to first full hour of data
        timestamp = float(timerow[0])+(timestamp-3600)
        counter = 11520  # holds number of measurements per hour, used in inner loop
        returnVal = []
        type = 'ACC'
        sum = 0
        divisor = 11520  # duplicate of counter, not changed in loop
        average = 0
        hours = 0

        # find length of file so we know when to stop, cutting any partial hours
        end = len(acclist) - arrayIndex
        leftOver = end % divisor
        end = end - leftOver
        leveler = (end - arrayIndex) % 10
        end = end - leveler

        # nested loop to calculate averages for the hours in the file, outer is for whole file, inner is for each hour
        # (end - divisor *20) this makes sure the last time this loop executes is on the last hour
        while (arrayIndex <= (end - divisor * 10)):
            sum = 0
            while (counter > 0):
                row = acclist[arrayIndex].split(',')

                # find resultant vector from components given
                magnitude = 0
                x = float(row[0])**2
                y = float(row[1])**2
                z = float(row[2])**2

                magnitude = (x+y+z)**(.5)

                sum += magnitude
                arrayIndex += 10  # of the values are collected
                counter -= 1
            average = sum / divisor
            #print(sum,average,divisor)
            returnVal.append(average)  # store the average for this hour in the return array
            counter = divisor
            hours += 1

        # commit list to db
        self.commitdb(returnVal, type)
