"""
@Ray Wei 2020-2021
@Daniel Stabile (UI, Alarms), Rishi Singhal (Bluetooth testing) 2020
@Yuexing Hao 2022(Connect with Azure Database)
Vita Innovations
"""
# from mask import Mask
import os
import sys
import psycopg2
from kivy.resources import resource_add_path, resource_find
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics import *
from kivy.metrics import dp
from kivy.properties import Property
from kivy.properties import ListProperty
from kivy.core.audio import SoundLoader
# from kivy.deps.sdl2 import sdl2, glew
from functools import partial
from random import random
import asyncio
import binascii
from bleak import BleakClient
from bleak import discover
from bleak.backends import characteristic
from kivy.core.window import Window
from kivy.uix.popup import Popup
from datetime import date
from datetime import datetime
import numpy as np
from collections import deque
from kivy.core.window import Window
from kivy.config import Config

Config.set('graphics', 'resizable', False)

VERSION = "Release 0.9.6"

# Seconds between each time the vitals table refreshes automatically.
SECS_PER_REFRESH = 0.5
# Whether or not to use bluetooth or to have purely simulated data.
# NOTE: Obsolete; leave as True. To simulate values, just pick the "00:SI:MU:LA:TE:00" address when adding a mask.
BLE_DEBUG = True
# Whether or not to store vitals on database.
DATABASE_DEBUG = False
mask_dict = dict()

WINDOW_WIDTH = 1366


dark_bgColor1 = (0,   0,   0, 1)
dark_bgColor2 = (.13, .13, .13, 1)
dark_bgColor3 = (.25, .25, .25, 1)
dark_bgColor4 = (.37, .37, .37, 1)
# greendark_accentColor1 = (.31, .7, .53, 1)
# greendark_accentColor2 = (.21, .45, .3, 1)
# purpledark_accentColor1 = (.44, .50, .67, 1)
# purpledark_accentColor2 = (.17, .27, .44, 1)
bluedark_accentColor1 = (.0, .47, .71, 1)
bluedark_accentColor2 = (.01, .24, .54, 1)
bluedark2_accentColor1 = (.0, .59, .78, 1)
bluedark2_accentColor2 = (.0, .47, .71, 1)
bluedark3_accentColor1 = (.01, .31, .53, 1)
bluedark3_accentColor2 = (0, .23, .39, 1)

dark_textColor = (.9, .97, .95, 1)

# ONLY change these colors
bgColor1 = dark_bgColor1
bgColor2 = dark_bgColor2
bgColor3 = dark_bgColor3
bgColor4 = dark_bgColor4
accentColor1 = bluedark3_accentColor1
accentColor2 = bluedark3_accentColor2
textColor = dark_textColor
redColor = (1, .26, .26, 1)
# DO not change the rest of the colors, they reference these ^

task = None

alarmStr = 'mp3/appointed-529.mp3'
# alarmStr = 'mp3/juntos-607.mp3'
# alarmStr = 'mp3/that-was-quick-606.mp3'
alarm = SoundLoader.load(alarmStr)
volume = 1

# inputHeight = dp(20)
# headerHeight = dp(30)

# inputFont = dp(20)
# headerFont = dp(30)
# titleFont = dp(40)

two_dec = "{:.2f}"
# Real SPO2 UUID
SPO2_CHAR_UUID = "00002a5f-0000-1000-8000-00805f9b34fb"
HR_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
TEMPERATURE_CHAR_UUID = "00001402-0000-1000-8000-00805f9b34fb0"
# Rishi's test UUID
# SPO2_CHAR_UUID = "E54B0002-67F5-479E-8711-B3B99198CE6C"

# Timed local memory parameters
track_interval = 2  # Store local vital at every track_interval minutes
deque_size = 120  # Store a maximum of deque_size vitals locally

# Vitals Percent Change value: in minutes
delta_period = 10

# Priority Scoring Method: Can be either 'NEWS','# Abnormal Vitals'
scoring_method = "NEWS"


class Mask():
    '''
    Class Mask: The object representing an individual mask.

    Attributes:
        addr - MAC address of the mask's bluetooth connection.
        num - Mask number AKA unique identifier of the mask.
        pui - Whether the wearer of the mask is a Patient Under Investigation.
        age - Mask wearer's age.
        sex - Mask wearer's sex.
        cur - Cursor for the currently connected database. Use this to execute commands to access and view the database.
        hr_val - Current heart rate detected by mask.
        spo2_val - Current blood oxygen level detected by mask.
        rr_val - Current respiratory rate detected by mask.
        temp_val - Current temperature detected by mask.
        min_hr & max_hr - Bounds for the acceptable heart rate thresholds.
        min_spo2 & max_spo2 - Bounds for the acceptable blood oxygen thresholds.
        min_rr & max_rr - Bounds for the acceptable respiratory rate thresholds.
        min_temp & max_temp - Bounds for the acceptable temperature thresholds.
        chart_elt - Created in update(), the visual representation of mask information displayed by the dashboard.
        bluetooth - Boolean for whether or not mask is simulated or using a real bluetooth connection.
    '''

    def __init__(self, addr, num, cc, esi, pui, avpu, eg, age, sex, cur):
        super(Mask, self).__init__()
        self.alarm_activated = {"spo2": False,
                                "hr": False, "rr": False, "temp": False}
        self.addr = addr
        self.num = num
        if cc == "" or cc == "-":
            self.cc = None
        else:
            self.cc = cc
        if esi == "" or esi == "-":
            self.esi = None
        else:
            self.esi = esi
        if pui == "" or pui == "-":
            self.pui = None
        else:
            self.pui = pui
        if avpu == "" or avpu == "-":
            self.avpu = None
        else:
            self.avpu = avpu
        if eg == "" or eg == "-":
            self.eg = None
        else:
            self.eg = eg
        if age == "" or age == "-":
            self.age = None
        else:
            self.age = age
        if sex == "" or sex == "-":
            self.sex = None
        else:
            self.sex = sex
        self.con = False
        self.wear = False
        self.battery = False
        self.hr_val = 85.0 + (18 * random())
        self.spo2_val = 89.0 + (9 * random())
        self.rr_val = 14.0 + (5 * random())
        self.temp_val = 97.5 + (random())
        self.max_hr = 100.0
        self.min_hr = 87.0
        self.max_spo2 = 100.0
        self.min_spo2 = 92.0
        self.max_rr = 20.0
        self.min_rr = 13.0
        self.max_temp = 98.0
        self.min_temp = 97.5
        self.stop = False
        self.cur = cur
        self.fname = "Test"
        self.lname = "Patient"
        # Changes in respective vitals, in percent
        self.delta_hr = 0
        self.delta_spo2 = 0
        self.delta_rr = 0
        # 5 different scoring methods, changeable in settings
        self.priority = 0
        self.news = 0
        self.news2 = 0
        self.mews = 0
        self.esi_sort = 0
        # Limited local storage of spo2, rr, and hr in the last x minutes.
        self.spo2_deque = deque([], deque_size)
        self.hr_deque = deque([], deque_size)
        self.rr_deque = deque([], deque_size)
        self.elapsed = 0  # time in seconds since mask was created
        if(BLE_DEBUG and self.addr != "00:SI:MU:LA:TE:00"):
            self.bluetooth = True  # SIMULATE address is the debug function for still simulating a mask's vitals even if bluetooth debug is turned on
        else:
            self.bluetooth = False
            self.con = True
            self.wear = True
            self.battery = True
        if(self.bluetooth):
            loop = asyncio.get_running_loop()
            loop.create_task(self.enable_notifs(addr))
            # t = threading.Thread(target=self.loop_in_thread, args=(loop, addr))
            # t.start()
        if(self.cur):
            # self.db_create_tables(self.cur)
            self.db_add_patient(self.cur)
            self.db_add_visit(self.cur)
            print("database stuff")
        self.update()

        # self.performBLE()
    '''
    Simulates new mask values and updates the mask chart element accordingly so that the dashboard displayes current information about mask.
    Should only be called internally by init init or externally by the clock, or else the vital delta calculations would be inaccurate.
    '''

    def update(self):
        if(not self.bluetooth):  # simulate vitals if we're not using a real bluetooth connection with a mask
            self.spo2_val += (.1*(random()-.5))
            self.hr_val += (.1*(random()-.5))
            self.rr_val += (.1*(random()-.5))
            self.temp_val += (.001*(random()-.5))
        # If the interval for recording vitals has passed, then record vitals in deques
        if(self.elapsed == 0 or self.elapsed % (60*track_interval) == 0):
            self.spo2_deque.appendleft(self.spo2_val)
            self.hr_deque.appendleft(self.hr_val)
            self.rr_deque.appendleft(self.rr_val)
        # If the period for calculating percent change is up, update vital deltas
        if(self.elapsed > delta_period*60):
            # print(self.hr_deque)
            # print("at " + str(self.elapsed) + " seconds, looking back at value " +
            #       str(self.hr_deque[int(delta_period/track_interval) - 1]))
            old_hr = self.hr_deque[int(delta_period/track_interval) - 1]
            old_spo2 = self.spo2_deque[int(delta_period/track_interval) - 1]
            old_rr = self.rr_deque[int(delta_period/track_interval) - 1]
            self.delta_hr = 100*(self.hr_val - old_hr)/old_hr
            self.delta_spo2 = 100*(self.spo2_val - old_spo2)/old_spo2
            self.delta_rr = 100*(self.rr_val - old_rr)/old_rr
            # print(self.delta_hr)
            # print(self.delta_spo2)
            # print(self.delta_rr)
        self.news = self.get_news()
        self.news2 = self.get_news2()
        self.mews = self.get_mews()
        self.esi_sort = self.get_ESI()
        self.elapsed += SECS_PER_REFRESH
        # Declares visual elements.
        new_elt = BoxLayout(size_hint_y=None, height=30,
                            pos_hint={'top': 1})
        pnum = Label(text=str(self.num), size_hint_x=.1, color=textColor)
        if(scoring_method == "NEWS"):
            pprio = Label(text=str(self.news),
                          size_hint_x=.1, color=textColor)
        elif(scoring_method == "NEWS2"):
            pprio = Label(text=str(self.news2),
                          size_hint_x=.1, color=textColor)
        elif(scoring_method == "MEWS"):
            pprio = Label(text=str(self.mews),
                          size_hint_x=.1, color=textColor)
        elif(scoring_method == "ESI"):
            pprio = Label(text=str(self.esi),
                          size_hint_x=.1, color=textColor)
        else:
            pprio = Label(text=str(self.priority),
                          size_hint_x=.1, color=textColor)
        if(self.con):
            # pcon = Label(text="Yes", size_hint_x=.1, color=textColor)
            pcon = Image(source="png/bluetooth_18dp.png",
                         color=textColor, size_hint_x=.03)
        else:
            # pcon = Label(text="No", size_hint_x=.1, color=textColor)
            pcon = Image(source="png/bluetooth_disabled_18dp.png",
                         color=redColor, size_hint_x=.03)
        if(self.wear):
            pwear = Image(source="png/mask_18dp.png",
                          color=textColor, size_hint_x=.03)
        else:
            pwear = Image(source="png/mask_disabled_18dp.png",
                          color=redColor, size_hint_x=.03)
        if(self.battery):
            pbatt = Image(source="png/recharge_battery_18dp.png",
                         color=textColor, size_hint_x=.03)
        else:
            pbatt = Image(source="png/empty_battery_18dp.png",
                         color=redColor, size_hint_x=.03)
        ppui = Label(text=str(self.pui), size_hint_x=.075,
                     color=textColor)
        page = Label(text=str(self.age), size_hint_x=.075,
                     color=textColor)
        psex = Label(text=str(self.sex), size_hint_x=.1,
                     color=textColor)
        # Handles text coloration based on whether or not each vital has exceeded threshold value
        vitals_exceeded = 0  # Keeps track of number of vitals out of threshold
        sound_alarm = False  # Set to true if any vital switches from normal to exceeding threshold
        spo2_text = str(round(self.spo2_val))
        hr_text = str(round(self.hr_val))
        rr_text = str(round(self.rr_val))
        # Only display the percent change if mask has been on long enough to calculate delta over set period of time
        if self.elapsed >= delta_period*60:
            if round(self.delta_spo2) != 0:
                spo2_text += " (" + str(round(self.delta_spo2)) + "%)"
            if round(self.delta_hr) != 0:
                hr_text += " (" + str(round(self.delta_hr)) + "%)"
            if round(self.delta_rr) != 0:
                rr_text += " (" + str(round(self.delta_rr)) + "%)"
        if(self.spo2_val < self.min_spo2 or self.spo2_val > self.max_spo2):
            pspo2 = Label(text=spo2_text, size_hint_x=.1,
                          color=redColor)
            if not self.alarm_activated["spo2"]:
                self.alarm_activated["spo2"] = True
                sound_alarm = True
            vitals_exceeded += 1
        else:
            pspo2 = Label(text=spo2_text, size_hint_x=.1,
                          color=textColor)
            self.alarm_activated["spo2"] = False
        if(self.hr_val < self.min_hr or self.hr_val > self.max_hr):
            phr = Label(text=hr_text, size_hint_x=.1,
                        color=redColor)
            if not self.alarm_activated["hr"]:
                self.alarm_activated["hr"] = True
                sound_alarm = True
            vitals_exceeded += 1
        else:
            phr = Label(text=hr_text, size_hint_x=.1,
                        color=textColor)
            self.alarm_activated["hr"] = False

        if(self.rr_val < self.min_rr or self.rr_val > self.max_rr):
            prr = Label(text=rr_text, size_hint_x=.1,
                        color=redColor)
            if not self.alarm_activated["rr"]:
                self.alarm_activated["rr"] = True
                sound_alarm = True
            vitals_exceeded += 1
        else:
            prr = Label(text=rr_text, size_hint_x=.1,
                        color=textColor)
            self.alarm_activated["rr"] = False
        if(self.temp_val < self.min_temp or self.temp_val > self.max_temp):
            ptemp = Label(text=str(round(self.temp_val, 1)), size_hint_x=.1,
                          color=redColor)
            if not self.alarm_activated["temp"]:
                self.alarm_activated["temp"] = True
                sound_alarm = True
            vitals_exceeded += 1
        else:
            ptemp = Label(text=str(round(self.temp_val, 1)), size_hint_x=.1,
                          color=textColor)
            self.alarm_activated["temp"] = False

        # Sound alarm, vary pitch based on number of
        self.priority = vitals_exceeded
        if (sound_alarm):
            alarm.pitch = 0.5 * vitals_exceeded
            alarm.volume = volume
            alarm.play()

        new_elt.add_widget(pnum)
        new_elt.add_widget(pprio)
        new_elt.add_widget(pcon)
        new_elt.add_widget(pwear)
        new_elt.add_widget(pbatt)
        new_elt.add_widget(ppui)
        new_elt.add_widget(page)
        new_elt.add_widget(psex)
        new_elt.add_widget(pspo2)
        new_elt.add_widget(phr)
        new_elt.add_widget(prr)
        new_elt.add_widget(ptemp)
        self.chart_elt = new_elt

        if(self.cur):
            self.db_update_readings(self.cur)

    # Calculate NEWS score based on current vitals.
    def get_news(self):
        news = 0
        if self.avpu and self.avpu != "Alert":
            news += 3
        if self.hr_val <= 40 or self.hr_val >= 131:
            news += 3
        elif self.hr_val > 110:
            news += 2
        elif self.hr_val <= 50 or self.hr_val > 90:
            news += 1
        if self.temp_val <= 95:
            news += 3
        elif self.temp_val >= 102.3:
            news += 2
        elif self.temp_val <= 96.8 or self.temp_val > 100.4:
            news += 1
        if self.rr_val <= 8 or self.rr_val >= 25:
            news += 3
        elif self.rr_val > 20:
            news += 2
        elif self.rr_val <= 11:
            news += 1
        if self.spo2_val <= 91:
            news += 3
        elif self.spo2_val <= 93:
            news += 2
        elif self.spo2_val <= 95:
            news += 1
        return news

    # Yuexing TODO: Calculate M-NEWS2 score based on current vitals
    def get_news2(self):
        news2 = 0
        if self.avpu and self.avpu != "Alert":
            news2 += 3
        if self.temp_val <= 95:
            news2 += 3
        elif self.temp_val >= 102.3:
            news2 += 2
        elif self.temp_val <= 96.8 or self.temp_val > 100.4:
            news2 += 1
        if self.rr_val <= 8 or self.rr_val >= 25:
            news2 += 3
        elif self.rr_val > 20:
            news2 += 2
        elif self.rr_val <= 11:
            news2 += 1
        return news2

    # Yuexing TODO: Calculate M-MEWS score based on current vitals.
    def get_mews(self):
        mews = 0
        if self.avpu and self.avpu == "Unresponsive":
            mews += 3
        if self.avpu and self.avpu == "Reacts to Pain":
            mews += 2
        if self.avpu and self.avpu == "Reacts to Voice":
            mews += 1
        if self.hr_val < 40 or self.hr_val > 110: 
            mews += 2
        elif self.hr_val <= 50 or self.hr_val > 100:
            mews += 1
        elif self.hr_val >= 130:
            mews += 3
        if self.temp_val <= 95:
            mews += 3
        elif self.temp_val >= 102.3:
            mews += 2
        elif self.temp_val <= 96.8 or self.temp_val > 100.4:
            mews += 1
        if self.rr_val <= 8 or self.rr_val >= 21:
            mews += 2
        elif self.rr_val >= 15:
            mews += 1
        elif self.rr_val >= 30:
            mews += 3
        return mews


    # Yuexing TODO: Sort the priority list by ESI score
    def get_ESI(self):
        esi_sort = 0
        if self.esi == 5:
            esi_sort += 5
        if self.esi == 4:
            esi_sprt += 4
        if self.esi == 3:
            esi_sort += 3
        if self.esi == 2:
            esi_sort+= 2
        if self.esi == 1:
            esi_sort += 1
        return esi_sort

    '''
    Bluetooth nonsense below.
    '''

    def spo2_notif_handler(self, sender, data):
        value = (data[1])
        print(value)
        self.spo2_val = value

    def hr_notif_handler(self, sender, data):
        value = (data[1])
        print(value)
        self.hr_val = value

    def temperature_notif_handler(self, sender, data):
        value = (data[1])
        print(value)
        self.temp_val = value

    # async def end_connection(self):
    #     async with BleakClient(self.addr) as client:
    #         await client.stop_notify
    #         await client.disconnect()

    async def enable_notifs(self, address):
        print("Notifs started")
        async with BleakClient(self.addr) as client:
            #     print("[Service] {0}: {1}".format(service.uuid, service.description))
            #     for char in service.characteristics:
            #         if "read" in char.properties:
            #             try:
            #                 value = bytes(await client.read_gatt_char(char.uuid))
            #             except Exception as e:
            #                 value = str(e).encode()
            #         else:
            #             value = None
            #         print(
            #             "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
            #                 char.uuid,
            #                 char.handle,
            #                 ",".join(char.properties),
            #                 char.description,
            #                 value,
            #             )
            #         )
            #         for descriptor in char.descriptors:
            #             value = await client.read_gatt_descriptor(descriptor.handle)
            #             print(
            #                 "\t\t[Descriptor] {0}: (Handle: {1}) | Value: {2} ".format(
            #                     descriptor.uuid, descriptor.handle, bytes(value)
            #                 )
            #             )
            while True:
                x = await client.is_connected()
                self.con = str(x)
                await client.start_notify(SPO2_CHAR_UUID, self.spo2_notif_handler)
                await client.start_notify(HR_CHAR_UUID, self.hr_notif_handler)
                # await client.start_notify(TEMPERATURE_CHAR_UUID, self.temperature_notif_handler)
                if(not self.con):
                    print("trying to end connection")
                    #  await client.stop_notify(TEMPERATURE_CHAR_UUID)
                    await client.stop_notify(SPO2_CHAR_UUID)
                    await client.stop_notify(HR_CHAR_UUID)
                    await client.disconnect()
                # await asyncio.sleep(0.1)

            print("Notifs stopped")

    def db_create_tables(self, cursor):
        """ create tables in the PostgreSQL database"""
        commands = (
            """
            CREATE TABLE patients (
                patient_id SERIAL PRIMARY KEY,
                patient_firstname VARCHAR(255) NOT NULL,
                patient_lastname VARCHAR(255) NOT NULL,
                patient_age INTEGER,
                patient_sex VARCHAR(255)
            )
            """,
            """
            CREATE TYPE Readings AS (
                timestamp TIMESTAMP,
                spo2 DOUBLE PRECISION,
                hr DOUBLE PRECISION,
                rr DOUBLE PRECISION,
                temp DOUBLE PRECISION
            )
            """,
            """
            CREATE TABLE visits (
                visit_id SERIAL PRIMARY KEY,
                patient_id SERIAL NOT NULL,
                date DATE NOT NULL,
                readings Readings[],
                FOREIGN KEY (patient_id)
                    REFERENCES patients (patient_id)
                    ON UPDATE CASCADE ON DELETE CASCADE
                )
            """)
        try:
            # create table one by one
            for command in commands:
                cursor.execute(command)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def db_add_patient(self, cursor):
        """ create tables in the PostgreSQL database"""
        command = """
            INSERT INTO patients(patient_firstname, patient_lastname, patient_age, patient_sex)
            VALUES(%s,%s,%s,%s) RETURNING patient_id;
         """
        data = (self.fname, self.lname, self.age, self.sex)
        try:
            cursor.execute(command, data)
            self.patient_id = cursor.fetchone()[0]
            print(self.patient_id)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def db_add_visit(self, cursor):
        """ create tables in the PostgreSQL database"""
        command = """
            INSERT INTO visits(patient_id, date, readings)
            VALUES(%s,%s,%s) RETURNING visit_id;
         """
        data = (self.patient_id, date.today(), [])
        try:
            cursor.execute(command, data)
            self.visit_id = cursor.fetchone()[0]
            print(self.visit_id)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def db_update_readings(self, cursor):
        """ create tables in the PostgreSQL database"""
        command = """
            UPDATE visits
                SET readings = readings || ROW(%s, %s, %s, %s, %s)::readings
                WHERE visit_id = %s
         """
        data = (datetime.now(), self.spo2_val,
                self.hr_val, self.rr_val, self.temp_val, self.visit_id)
        print("updating")
        try:
            cursor.execute(command, data)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)


class DashboardWindow(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Clock.schedule_interval(self.update, 1)
        loop = asyncio.get_event_loop()
        global task
        task = loop.create_task(self.run_update())
        Window.bind(on_request_close=self.on_request_close)
        self.sort_by_id = True
        self.sort_by_priority = False
        if(DATABASE_DEBUG):
            try:
                self.conn = psycopg2.connect(
                    host="vita.cj39t57gvtxl.us-east-2.rds.amazonaws.com",
                    database="vita_db",
                    user="vita_innovations",
                    password="Vita321!")
                self.conn.set_session(autocommit=True)
                self.cur = self.conn.cursor()
                # execute a statement
                print('PostgreSQL database version:')
                self.cur.execute('SELECT version()')
                # display the PostgreSQL database server version
                db_version = self.cur.fetchone()
                print(db_version)
            except psycopg2.OperationalError:
                self.conn = None
                self.cur = None
        else:
            self.conn = None
            self.cur = None

    def sort_by_id_func(self, instance):
        # Fetch the other sorting button because we must deactivate it to activate this one
        instance2 = self.ids.sort_priority_button
        self.sort_by_id = True
        self.sort_by_priority = False
        instance.image_source = "png/arrow_up_18dp.png"
        instance2.image_source = "png/arrow_down_black_18dp.png"
        self.ids.sort_priority_button.frame_color = bgColor1
        self.ids.sort_id_button.frame_color = textColor
        self.update(False)

    def sort_by_priority_func(self, instance):
        # Fetch the other sorting button because we must deactivate it to activate this one
        instance2 = self.ids.sort_id_button
        self.sort_by_id = False
        self.sort_by_priority = True
        instance.image_source = "png/arrow_down_18dp.png"
        instance2.image_source = "png/arrow_up_black_18dp.png"
        self.ids.sort_id_button.frame_color = bgColor1
        self.ids.sort_priority_button.frame_color = textColor
        self.update(False)

    def on_request_close(self, *args):
        self.exitpopup("Quit", "Are you sure you want to quit?")
        return True

    def close(self, *args):
        if self.conn is not None:
            # close communication with the PostgreSQL database server
            self.cur.close()
            # commit the changess
            self.conn.commit()
            self.conn.close()
        App.get_running_app().stop()

    def exitpopup(self, title, text):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=text))
        exit_button = Button(text='Quit', size_hint=(1, 0.25))
        cancel_button = Button(text='Cancel', size_hint=(1, 0.25))
        subcontent = BoxLayout(orientation='horizontal', spacing=dp(5))
        subcontent.add_widget(exit_button)
        subcontent.add_widget(cancel_button)
        content.add_widget(subcontent)
        self.popup = Popup(title=title, content=content,
                           size_hint=(None, None), size=(300, 150))
        exit_button.bind(on_release=self.close)
        cancel_button.bind(on_release=lambda *args: self.popup.dismiss())
        self.popup.open()

    '''
    Adds a mask onto the application based on user input.
    '''

    def add_mask(self):

        # For debug codes
        global task

        # Parses user input into fields for new mask
        mask_addr = self.ids.addr_spinner.text
        mask_cc = self.ids.cc_spinner.text
        mask_esi = self.ids.esi_spinner.text
        mask_num = self.ids.mask_num_inp.text
        mask_pui = self.ids.pui_spinner.text
        mask_avpu = self.ids.avpu_spinner.text
        mask_eg = self.ids.eg_spinner.text
        mask_age = self.ids.age_inp.text
        mask_sex = self.ids.sex_spinner.text
        masks_container = self.ids.masks

        # Checks fields to see if they are in appropriate format
        if mask_num.isnumeric() and mask_num not in mask_dict and len(mask_addr.replace(':', '')) == 12 and mask_age is not None:
            # New mask is declared based on parsed input and then added to dictionary
            new_mask = Mask(mask_addr, mask_num, mask_cc, mask_esi, mask_pui, mask_avpu, mask_eg,
                            mask_age, mask_sex, self.cur)
            mask_dict[mask_num] = new_mask
            # Row is created inside the dashboard chart. This row will hold the chart element that is attached to the new mask, which will display all mask info.
            row = GridButton(cols=1, rows=1, size_hint_y=None, height=40,
                             pos_hint={'top': 1}, id=mask_num, background_normal='', background_color=bgColor2)
            row.bind(on_press=self.on_chart_select)
            row.add_widget(new_mask.chart_elt)
            masks_container.add_widget(row)
            # masks_container.add_widget(new_mask.chart_elt)
            self.ids.addr_spinner.text = "-"
            self.ids.mask_num_inp.text = ""
            self.ids.cc_spinner.text = "-"
            self.ids.esi_spinner.text = "-"
            self.ids.pui_spinner.text = "-"
            self.ids.avpu_spinner.text = "-"
            self.ids.eg_spinner.text = "-" 
            self.ids.age_inp.text = ""
            self.ids.sex_spinner.text = "-"
        elif mask_num == "mega update":
            for i in range(0, 2000):
                self.update(True)
            print("Debug Command: Updating 2000 times (%d minutes)!" %
                  (2000*SECS_PER_REFRESH/60))
        elif mask_num == "freeze":
            if task.cancelled() == False:
                task.cancel()
                print("Debug Command: Freezing updates")
            else:
                print("Fail Debug Command: Task already frozen!")
        elif mask_num == "go":
            if task.cancelled():
                task = asyncio.get_event_loop().create_task(self.run_update())
                print("Debug Command: Restarting updates")
            else:
                print("Fail Debug Command: Already going!")
    '''
    Updates the mask chart when called, usually be 1-second clock or any other function that changes/adds/removes mask info.

    Parameters:
        deltaTime - Ignore
    '''

    async def run_update(self):
        while True:
            print('Refreshing UI')
            self.update(True)
            await asyncio.sleep(SECS_PER_REFRESH)

    '''
    Runs updates on the window, such as regular mask updates (if true) or UI updates based on user input (sorting, adding/deleting masks, etc)
    
    Attributes:
        update_mask - Boolean to call the mask's update function. Should only be true when called by the regular clock, or else the vital delta calculations would be inaccurate.
    '''

    def update(self, update_mask):

        global volume
        global delta_period
        global scoring_method
        masks_container = self.ids.masks
        # Sort masks by priority so that the highest priority shows up at top
        # Choose what to sort by?
        # TODO: Add sorting for NEWS2, MEWS, and ESI
        if(self.sort_by_id):
            sorted_masks = sorted(mask_dict.values(),
                                  key=lambda mask: mask.num, reverse=True)
        elif(self.sort_by_priority):
            if(scoring_method == "NEWS"):
                sorted_masks = sorted(mask_dict.values(),
                                      key=lambda mask: (mask.news, -int(mask.num)))
            elif(scoring_method == "NEWS2"):
                sorted_masks = sorted(mask_dict.values(),
                                      key=lambda mask: (mask.news2, -int(mask.num)))
            elif(scoring_method == "MEWS"):
                sorted_masks = sorted(mask_dict.values(),
                                      key=lambda mask: (mask.mews, -int(mask.num)))
            elif(scoring_method == "ESI"):
                sorted_masks = sorted(mask_dict.values(),
                                      key=lambda mask: (mask.esi, -int(mask.num)))
        else:
            sorted_masks = sorted(mask_dict.values(),
                                  key=lambda mask: mask.num)
        # First loop cleans up rows and deletes rows that correspond to deleted masks
        for child in masks_container.children:
            if child.id in mask_dict:
                # Remove old mask chart element from row
                child.clear_widgets()
            else:
                masks_container.remove_widget(child)
        mask_idx = 0
        # Second loop sorts masks and repopulates rows
        for child in masks_container.children:
            mask = sorted_masks[mask_idx]
            # In event of sorting, make sure the row is correctly updated to have the idea of its new contained mask
            child.id = sorted_masks[mask_idx].num
            mask_idx += 1
            # Update mask values and fetches new mask chart element.
            if update_mask:
                mask.update()
            # Puts in row the updated mask chart element based on current information.
            child.add_widget(mask.chart_elt)

        volume = self.ids.slider_volume.value / 100.0
        scoring_method = self.ids.settings_priority_spinner.text
        if self.ids.settings_delta_spinner.text == '4 min':
            delta_period = 4
        elif self.ids.settings_delta_spinner.text == '10 min':
            delta_period = 10
        elif self.ids.settings_delta_spinner.text == '30 min':
            delta_period = 30
        elif self.ids.settings_delta_spinner.text == '1 hr':
            delta_period = 60
        elif self.ids.settings_delta_spinner.text == '2 hr':
            delta_period = 120
        elif self.ids.settings_delta_spinner.text == '4 hr':
            delta_period = 240
    '''
    Called when user clicks on a row inside the mask chart.
    Fetches all info pertaining to the mask that corresponds to the selected row,
    and displays the info in the settings menu.
    '''

    def on_chart_select(self, instance):
        print("selected mask #", instance.id)
        self.toggle_settings(False)
        self.ids.settings_mask_num.text = str(instance.id)
        self.ids.settings_cc_spinner.text = str(mask_dict[instance.id].cc)
        self.ids.settings_esi_spinner.text = str(mask_dict[instance.id].esi)
        self.ids.settings_pui_spinner.text = str(mask_dict[instance.id].pui)
        self.ids.settings_avpu_spinner.text = str(mask_dict[instance.id].avpu)
        self.ids.settings_eg_spinner.text = str(mask_dict[instance.id].eg)
        if str(mask_dict[instance.id].age) == "None":
            self.ids.settings_age_inp.text = ""
            self.ids.settings_age_inp.hint_text = "None"
        else:
            self.ids.settings_age_inp.text = str(mask_dict[instance.id].age)
        self.ids.settings_sex_spinner.text = str(mask_dict[instance.id].sex)
        self.ids.settings_min_spo2.text = str(mask_dict[instance.id].min_spo2)
        self.ids.settings_max_spo2.text = str(mask_dict[instance.id].max_spo2)
        self.ids.settings_min_hr.text = str(mask_dict[instance.id].min_hr)
        self.ids.settings_max_hr.text = str(mask_dict[instance.id].max_hr)
        self.ids.settings_min_rr.text = str(mask_dict[instance.id].min_rr)
        self.ids.settings_max_rr.text = str(mask_dict[instance.id].max_rr)
        self.ids.settings_min_temp.text = str(mask_dict[instance.id].min_temp)
        self.ids.settings_max_temp.text = str(mask_dict[instance.id].max_temp)

    '''
    Called when user clicks "update mask" button on the settings menu.
    Takes all user input inside the fields of the settings menu and updates mask info accordingly.
    If no mask is currently pulled up in the settings menu, does nothing.
    '''

    def on_mask_update(self):
        mask_num = self.ids.settings_mask_num.text
        if mask_num != "N/A":
            mask_dict[mask_num].pui = self.ids.settings_pui_spinner.text
            mask_dict[mask_num].cc = self.ids.settings_cc_spinner.text
            mask_dict[mask_num].esi = self.ids.settings_esi_spinner.text
            mask_dict[mask_num].avpu = self.ids.settings_avpu_spinner.text
            mask_dict[mask_num].eg = self.ids.settings_eg_spinner.text
            mask_dict[mask_num].age = self.ids.settings_age_inp.text
            mask_dict[mask_num].sex = self.ids.settings_sex_spinner.text
            mask_dict[mask_num].min_spo2 = float(
                self.ids.settings_min_spo2.text)
            mask_dict[mask_num].max_spo2 = float(
                self.ids.settings_max_spo2.text)
            mask_dict[mask_num].min_hr = float(
                self.ids.settings_min_hr.text)
            mask_dict[mask_num].max_hr = float(
                self.ids.settings_max_hr.text)
            mask_dict[mask_num].min_rr = float(
                self.ids.settings_min_rr.text)
            mask_dict[mask_num].max_rr = float(
                self.ids.settings_max_rr.text)
            mask_dict[mask_num].min_temp = float(
                self.ids.settings_min_temp.text)
            mask_dict[mask_num].max_temp = float(
                self.ids.settings_max_temp.text)
            self.update(False)

    '''
    Called when user clicks "delete mask" button on the settings menu.
    Deletes the mask that is currently selected in the settings menu.
    If no mask is currently pulled up in the settings menu, does nothing.
    '''

    def on_mask_delete(self):
        mask_num = self.ids.settings_mask_num.text
        if mask_num != "N/A":
            # if(BLE_DEBUG):
            #     loop = asyncio.get_running_loop()
            #     loop.create_task(mask_dict[mask_num].end_connection())
            mask_dict[mask_num].con = False
            # Remove mask from dictionary.
            mask_dict.pop(mask_num, None)
            # Deselects the mask.
            self.ids.settings_mask_num.text = "N/A"
            self.toggle_settings(True)
            masks_container = self.ids.masks
            for child in masks_container.children:
                if child.id not in mask_dict:
                    masks_container.remove_widget(child)
            self.update(False)

    def toggle_settings(self, disabled):
        if bool:
            self.ids.settings_min_spo2.text = "-"
            self.ids.settings_min_hr.text = "-"
            self.ids.settings_min_rr.text = "-"
            self.ids.settings_min_temp.text = "-"
            self.ids.settings_max_spo2.text = "-"
            self.ids.settings_max_hr.text = "-"
            self.ids.settings_max_rr.text = "-"
            self.ids.settings_max_temp.text = "-"
            self.ids.settings_cc_spinner.text = "-"
            self.ids.settings_esi_spinner.text = "-"
            self.ids.settings_pui_spinner.text = "-"
            self.ids.settings_avpu_spinner.text = "-"
            self.ids.settings_eg_spinner.text = "-"
            self.ids.settings_age_inp.text = "-"
            self.ids.settings_sex_spinner.text = "-"
        self.ids.settings_min_spo2.disabled = disabled
        self.ids.settings_min_hr.disabled = disabled
        self.ids.settings_min_rr.disabled = disabled
        self.ids.settings_min_temp.disabled = disabled
        self.ids.settings_max_spo2.disabled = disabled
        self.ids.settings_max_hr.disabled = disabled
        self.ids.settings_max_rr.disabled = disabled
        self.ids.settings_max_temp.disabled = disabled
        self.ids.settings_pui_spinner.disabled = disabled
        self.ids.settings_cc_spinner.disabled = disabled
        self.ids.settings_esi_spinner.disabled = disabled
        self.ids.settings_avpu_spinner.disabled = disabled
        self.ids.settings_eg_spinner.disabled = disabled
        self.ids.settings_age_inp.disabled = disabled
        self.ids.settings_sex_spinner.disabled = disabled

    '''
    Called when the user clicks the scan button.
    Used to refresh the list of addresses the user may connect to.
    If bluetooth debugging is off, pulls up hardcoded list of simulated addresses.
    '''

    def see_addresses(self):
        if(BLE_DEBUG is True):
            print("Scanning")
            self.ids.addr_spinner.values = [
                "Scanning..."]
            self.ids.addr_spinner.text = "Scanning..."
            loop = asyncio.get_running_loop()
            loop.create_task(self.discover())

        else:
            self.ids.addr_spinner.values = [
                "23:41:3c:32:2c:25", "32:64:d3:12:64:3a"]

    async def discover(self):
        devices = await discover()
        addr_list = (device.address for device in devices)
        simulate_addr = ["00:SI:MU:LA:TE:00"]
        self.ids.addr_spinner.values = addr_list
        self.ids.addr_spinner.values = self.ids.addr_spinner.values + simulate_addr
        self.ids.addr_spinner.text = "Scanning Done"
        print("Scanning done")
        for d in devices:
            print(d)


class DashboardApp(App):
    # Resize and center screen
    initial_center = Window.center
    Window.size = (WINDOW_WIDTH, 768)
    Window.left -= Window.center[0] - initial_center[0]
    Window.top -= Window.center[1] - initial_center[1]
    bgColor1 = bgColor1
    bgColor2 = bgColor2
    bgColor3 = bgColor3
    bgColor4 = bgColor4
    accentColor1 = accentColor1
    accentColor2 = accentColor2
    textColor = textColor
    redColor = redColor

    def build(self):
        self.title = 'VitalMask Desktop ' + VERSION
        self.icon = 'logo_black.png'
        return DashboardWindow()


class GridButton(GridLayout, Button):
    id = Property("No Mask Number!")

    def bind(self, **kwargs):
        Button.bind(self, **kwargs)


async def run_app(other_task):
    '''This method, which runs Kivy, is run by the asyncio loop as one of the
    coroutines.
    '''
    da = DashboardApp()
    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    await da.async_run()  # run Kivy
    print('App done')
    # now cancel all the other tasks that may be running
    other_task.cancel()


async def idle():
    '''This method is also run by the asyncio loop and periodically prints
    something.
    '''
    try:
        while True:
            print('Idle')
            await asyncio.sleep(2)
    except asyncio.CancelledError as e:
        print('Cancelled', e)
    finally:
        # when cancelled, print that it finished
        print('Done idling')


def main_func():
    def root_func():
        '''This will run both methods asynchronously and then block until they
        are finished
        '''
        other_task = asyncio.ensure_future(idle())
        return asyncio.gather(run_app(other_task), other_task)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(root_func())
    print("bye!")
    loop.close()


if __name__ == '__main__':
    main_func()
