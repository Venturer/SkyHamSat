# -*- coding: utf-8 -*-
"""SatPredicter.

    A Qt5 based program for Python3.
    A text edit and graphs are used for output. The
    text edit and graphs can be re-sized by a splitter.
    """

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

# Version   1.0, March 2018
#           1.1 August 2018

# standard imports:

import json
import math
import sys
import urllib.request
from decimal import Decimal, localcontext, ROUND_DOWN
from pprint import pprint

# PyQt interface imports, Qt5
import PyQt5.uic as uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


# Third party modules:
import qtawesome as qta
import numpy as np
from skyfield.api import Topos, load, Angle

# Project modules:

# Graph
from graphqt5 import Graph, Polar, reCreateGraph


JULIAN_SEC = 1 / 86400

home = Topos('51.38833333333 N', '0.75416666666 W', elevation_m=100)

LOCALTIME = False

ts = load.timescale()

class MainApp(QMainWindow):
    """Main Qt5 Window."""

    lines = []
    next_pass_lines = []
    next_pass_polar_lines = []

    satellite_body_objects = []  # List of list[PyEphem satellite body objects, NORAD satellite number]
    satellite_data = None  # Dictionary of satellite data dictionaries
    satellites = None

    # Graph scales
    hours_to_show = 3

    upcoming_passes_graph = None
    next_passes_graph = None
    current_pass_graph = None

    showDebug = True  # set to False to disable debug displays

    def __init__(self):

        global myLocation

        """MainApp Constructor."""

        # TODO add favourites
        # FIXME fix multiple entries in satslist.csv for same satellite_name
        # TODO add save number of passes as settings
        # TODO add text splitter position as settings
        # TODO save changed location information

        # call inherited init
        super().__init__()

        # Load the GUI definition file
        # use 2nd parameter self so that events can be overridden
        self.ui = uic.loadUi('SkyHamSat.ui', self)

        download_tle_icon = qta.icon('fa.download', color='blue')
        self.pushButtonDownloadTLEs.setIcon(download_tle_icon)

        download_satellite_info_icon = qta.icon('fa.download', color='darkgreen')
        self.pushButtonDownloadSatInfo.setIcon(download_satellite_info_icon)

        # Connect action signals to slot methods
        # methods of the form:
        # self.on_componentName_signalName
        # are connected automatically from the ui file
        self.checkBoxTransponder.stateChanged.connect(self.on_checkboxes_changed)
        self.checkBoxBeacon.stateChanged.connect(self.on_checkboxes_changed)
        self.checkBoxDownlink.stateChanged.connect(self.on_checkboxes_changed)
        self.checkBoxUplink.stateChanged.connect(self.on_checkboxes_changed)
        self.comboBoxMode.editTextChanged.connect(self.on_checkboxes_changed)

        # Create labels to contain the graphs
        self.labelGraph = QLabel()
        self.labelPolarShowPasses = QLabel()
        self.labelPolarCurrentPass = QLabel()

        # Add the labels containing the graph to the scroll areas in the ui file
        self.scrollArea.setWidget(self.labelGraph)
        self.scrollAreaShowPasses.setWidget(self.labelPolarShowPasses)
        self.scrollAreaCurrentPass.setWidget(self.labelPolarCurrentPass)

        # Create an object to save and restore settings
        self.settings = QSettings('G4AUC', 'SkyHamSat')
        # self.settings.clear()

        # restore window position etc. from saved settings
        self.restoreGeometry(self.settings.value('geometry', type=QByteArray))

        self.setWindowTitle('SkyHamSat')

        # Show the Application
        self.show()

        # restore the splitter positions after the app is showing
        self.splitter_v_position = self.settings.value('splitterVposn', 150)
        self.splitterV.moveSplitter(int(self.splitter_v_position), 1)
        self.splitter_h_position = self.settings.value('splitterHposn1', 300)
        self.splitterH.moveSplitter(int(self.splitter_h_position), 1)
        self.splitter_h_position = self.settings.value('splitterHposn2', 600)
        self.splitterH.moveSplitter(int(self.splitter_h_position), 2)

        # restore other settings
        lat = self.settings.value('mylatitude', '51.38833333333 N', type=str)
        self.my_latitude.setText(lat)
        long = self.settings.value('mylongitude', '0.75416666666 W', type=str)
        self.my_longitude.setText(long)
        elevation = self.settings.value('myelevation', 100.0, type=float)
        self.my_elevation.setText(f'{elevation:0.1f}')
        home = Topos(lat, long, elevation_m=elevation)

        # Create graphs with texts shown but no lines yet
        self.draw_graphs()

        self.set_up_satellite_data()

    @pyqtSlot(int)
    @pyqtSlot(str)
    def on_checkboxes_changed(self, *args):
        """Actions when any of the checkboxes are changed."""

        # self.filtered_satellites = self.satellites_filtered_by_check_boxes()
        # self.filtered_satellites = [s for s in self.satellites_filtered_by_check_boxes()]

        self.fill_select_satellite_combo()
        self.fill_combo_box_with_list_of_modes()

    @pyqtSlot(int)
    def on_spinBoxNextPasses_valueChanged(self, value):
        """Actions when the value is changed."""

        self.draw_next_passes_for_selected_satellite()

    @pyqtSlot(int)
    def on_comboBoxMode_currentIndexChanged(self, index):
        """Actions when the index is changed."""

        self.fill_select_satellite_combo()
        pass

    @pyqtSlot()
    def on_pushButtonDownloadTLEs_clicked(self):
        """Slot triggered when the button is clicked.

            calls self.load_tles() to start the
            the method that gets the TLEs from
            celestrak.com/NORAD.
            """

        spin_icon = qta.icon('fa.spinner', color='red',
                             animation=qta.Spin(self.pushButtonDownloadTLEs))
        self.pushButtonDownloadTLEs.setIcon(spin_icon)

        # self.repaint()
        self.update()

        self.display_on_upcoming_passes()  # blank line
        self.load_tles()
        download_icon = qta.icon('fa.download', color='blue')
        self.pushButtonDownloadTLEs.setIcon(download_icon)
        # self.repaint()
        self.update()

    @pyqtSlot()
    def on_pushButtonNextPasses_clicked(self):
        """Slot triggered when the button is clicked.

            Display upcoming passes in the Left text pane.
            """

        self.clear_upcoming_passes_display()

        self.display_upcoming_passes()

    @pyqtSlot()
    def on_pushButtonPlotPass_clicked(self):
        """Slot triggered when the button is clicked.

            Display next passes for the selected satellite
            in the Right text pane.
            """

        self.clear_selected_satellite_passes_display()

        self.display_next_passes_for_selected_satellite()

    @pyqtSlot()
    def on_pushButtonDownloadSatInfo_clicked(self):
        """Slot triggered when the button is clicked.

            Download satellite info and save as statslist.csv
            Filter on active satellites from the file
            create a list of dicts
            Create satslist.json file
            call set_up_satellite_data to reload the json file
            """

        # Download satellite info and save as statslist.csv
        self.get_satellite_info()

        default = {'Satellite': '', 'Number': '', 'Transponder Uplink': [], 'Transponder Downlink': [], 'Uplinks': [],
                   'Downlinks': [], 'Beacons': [], 'Modes': [], 'Callsign': '', 'Status': ''}
        csv_field_names = ['Satellite', 'Number', 'Uplink', 'Downlink', 'Beacon', 'Mode', 'Callsign', 'Status']

        lines = file_lines('satslist.csv')

        # Generate the active satellites from the file
        filter_active = (csv for csv in lines if csv.split(';')[7] == 'active' or 'operational')

        # create a list of dicts using a comprehension by zipping the key names
        # with the csv items
        active_sats_list = [dict(zip(csv_field_names, (s.strip() for s in sat.strip().split(';'))))
                            for sat in filter_active]

        # remove duplicates by using satellite_name numbers
        sat_number_list = []
        for sat in active_sats_list[:]:
            if sat['Number'] in sat_number_list:
                active_sats_list.remove(sat)
            else:
                sat_number_list.append(sat['Number'])

        sats_dict = {}
        for s in active_sats_list:

            sat_dict = default.copy()
            for k in ['Satellite', 'Number', 'Callsign', 'Status']:
                sat_dict[k] = s[k]

            if s['Uplink']:
                if '-' in s['Uplink']:
                    sat_dict['Transponder Uplink'] = s['Uplink'].split('-')
                else:
                    sat_dict['Uplinks'] = s['Uplink'].split('/')

            if s['Downlink']:
                if '-' in s['Uplink']:
                    sat_dict['Transponder Downlink'] = s['Downlink'].split('-')
                else:
                    sat_dict['Downlinks'] = s['Downlink'].split('/')

            if s['Beacon']:
                sat_dict['Beacons'] = s['Beacon'].split('/')

            if s['Mode']:
                sat_dict['Modes'] = s['Mode'].replace('bps ', 'bps:').split(' ')

            sats_dict[s['Satellite']] = sat_dict

        with open('satslist.json', 'w') as f:
            json.dump(sats_dict, f)

        self.set_up_satellite_data()

        QMessageBox.information(self, "Satellite Information",
                                'Satellite information downloaded from JE9PEL,\nrestart application to take effect.',
                                QMessageBox.Ok)

    @pyqtSlot(int)
    def on_comboBoxSelectSatelllite_currentIndexChanged(self, *args):
        """Re-draw graphs on change of current index."""

        self.draw_next_passes_for_selected_satellite()
        self.selected_satellite_info()
        pass

    def decode_tles(self):
        """Decode the saved satellite TLEs in the text file
            'satellites.tle' to PyEphem satellite body objects.

            Returns -> list of [PyEphem EarthSatellite body object, sat_number]
            """

        with open('satellites.tle', 'r') as f:
            satellite_tles = f.read()

        data_lines = satellite_tles.splitlines()

        satellite_objects = []

        for idx in range(0, len(data_lines), 3):
            sat_number = data_lines[idx + 2].split(' ')[1]
            satellite_objects.append([ephem.readtle(data_lines[idx], data_lines[idx + 1],
                                                    data_lines[idx + 2]),
                                      sat_number])

        return satellite_objects

    def get_satellite_tles(self):
        """Get all the amateur satellite TLEs from celestrak.

            save the TLEs in text file satellites.tle.
            """

        req = urllib.request.Request("http://celestrak.com/NORAD/elements/amateur.txt")
        response = urllib.request.urlopen(req)
        data = response.read().decode().splitlines()

        with open('satellites.tle', 'w') as f:
            for line in data:
                f.write(line + '\n')

    def get_satellite_info(self):
        """Get all the amateur satellite information from JE9PEL.

            http://www.ne.jp/asahi/hamradio/je9pel/satslist.csv

            save the info in csv file satslist.csv.
            """

        req = urllib.request.Request("http://www.ne.jp/asahi/hamradio/je9pel/satslist.csv")
        response = urllib.request.urlopen(req)
        data = response.read().decode().splitlines()

        with open('satslist.csv', 'w', encoding='utf-8') as f:
            for line in data:
                f.write(line + '\n')

    def selected_satellite_info(self):
        """Display the info for the selected satellite in
            the features line edit and the frequencies into
            the selected_frequencies combo box.
            """

        selected_satellite = self.comboBoxSelectSatelllite.itemData(self.comboBoxSelectSatelllite.currentIndex())
        if selected_satellite is None:
            return  # Will be None if combo box is cleared

        # Fill satelliteFeatures line edit and selected_frequencies combo box
        info = ''
        frequencies = []
        selected_satellites_generator = (s for s in self.satellites.values()
                                         if s['Satellite'] == selected_satellite)

        for s in selected_satellites_generator:
            for k, inf in s.items():
                if not inf:
                    continue

                if isinstance(inf, str):
                    info += f'{k}: {inf} '

                if isinstance(inf, list):
                    info += f'{k}: '
                    for L in inf:
                        info += L + '-'
                        # Append anything that appears to be a frequency
                        try:
                            if k != 'modes':
                                float(L)
                                frequencies.append(L)
                        except ValueError:
                            pass  # Ignore if the string cannot be converted to float
                    info = info.rstrip('-') + ' '

        self.satelliteFeatures.setText(info)

        self.selected_frequencies.clear()
        self.selected_frequencies.addItems(frequencies)

    def fill_combo_box_with_list_of_modes(self):
        """fill comboBoxModes with list of modes
            from the filtered satellites.
            """

        mode_list = []

        for s in self.satellites.values():
            hasTransponder = self.checkBoxTransponder.isChecked() and s['Transponder Uplink']
            hasUplink = self.checkBoxUplink.isChecked() and s['Uplinks']
            hasDownlink = self.checkBoxDownlink.isChecked() and s['Downlinks']
            hasBeacon = self.checkBoxBeacon.isChecked() and s['Beacons']

            if any([hasTransponder, hasUplink, hasDownlink, hasBeacon]):

                if s['Modes']:
                    for m in s['Modes']:
                        mode_list.append(m)

        # Remove duplicates
        mode_list = list(set(mode_list))

        mode_list.sort()

        # Fill mode combo box
        self.comboBoxMode.clear()
        self.comboBoxMode.addItem('Any')
        for mode in mode_list:
            self.comboBoxMode.addItem(mode)
        self.comboBoxMode.setCurrentIndex(0)

    def satellites_filtered_by_check_boxes(self, dont_filter=False):
        """Generator to provide self.satellites filtered by state of
            the check boxes.

            yields -> a satellite dict
            """
        mode = self.comboBoxMode.currentText()
        for s in self.satellites.values():
            hasTransponder = self.checkBoxTransponder.isChecked() and s['Transponder Uplink']
            hasUplink = self.checkBoxUplink.isChecked() and s['Uplinks']
            hasDownlink = self.checkBoxDownlink.isChecked() and s['Downlinks']
            hasBeacon = self.checkBoxBeacon.isChecked() and s['Beacons']
            hasMode = (mode == 'Any') or (mode in s['Modes'])

            if any([hasTransponder, hasUplink, hasDownlink, hasBeacon, dont_filter]) and hasMode:
                yield s

    def transit_list_sorted_by_time(self):
        """:returns: [rise time: Julian, transit time: Julian, set time: Julian,
                        satellite name: string]
            """
        transit_list = []

        for v in self.satellites_filtered_by_check_boxes():
            sat = v['Satellite']
            pass_list = self.get_next_passes(sat, self.spinBoxNextPasses.value())

            pass_info = [0, 0, 0, sat]
            for pass_event in pass_list:
                if pass_event[1] == 'rise':
                    pass_info[0] = pass_event[0].tt
                elif pass_event[1] == 'transit':
                    pass_info[1] = pass_event[0].tt
                elif pass_event[1] == 'set':
                    pass_info[2] = pass_event[0].tt
                    transit_list.append(pass_info)
                    pass_info = [0, 0, 0, sat]

            if not pass_list:
                transit_list.append([0, 0, 0, sat])

        transit_list.sort()

        return transit_list

    def fill_select_satellite_combo(self, dontFilter=False):
        """Fills the Select Satellite combo box with the satellites in the TLE."""

        satellites = []
        self.comboBoxSelectSatelllite.clear()

        for v in self.satellites_filtered_by_check_boxes():
            satellite = v['Satellite']
            try:
                # r = myLocation.next_pass(satellite)
                satellites.append((satellite, satellite))
            except ValueError:
                pass  # Not above horizon here in next 24 hours

        satellites.sort()
        for s in satellites:
            self.comboBoxSelectSatelllite.addItem(s[0], s[1])

        self.comboBoxSelectSatelllite.setCurrentIndex(0)

    def set_up_satellite_data(self):
        """Set up the satellite data."""

        # Get the satelliteBodyObjects from the TLEs file
        stations_url = 'http://celestrak.com/NORAD/elements/amateur.txt'
        self.satellite_body_objects = load.tle_file(stations_url)

        self.by_number = {sat.model.satnum : sat for sat in self.satellite_body_objects}

        # Get the satellite data from the json file
        with open('satslist.json', 'r') as f:
            self.satellite_data = json.load(f)

        # Merge the two

        # list of NORAD numbers in self.satelliteBodyObjects
        numbers = {sat.model.satnum: sat for sat in self.satellite_body_objects}

        # Create a dict of satellite_data dicts where the NORAD numbers are also
        # in satellite_body_objects, i.e. where we have both TLEs and satellite_name info
        self.satellites = {s: self.satellite_data[s] for s in self.satellite_data
                           if self.satellite_data[s]['Number'] in str(numbers.keys())}

        # Fill the modes and Select Satellite combo boxes
        self.fill_combo_box_with_list_of_modes()
        self.fill_select_satellite_combo()

        # Start the Auto-updater
        self.auto_update_timer = QTimer()
        self.auto_update_timer.timeout.connect(self.on_auto_update_timer)
        self.auto_update_timer.start(1 * 1000)

        # Start the clock-updater
        self.clock_update_timer = QTimer()
        self.clock_update_timer.timeout.connect(self.on_clock_update)
        self.clock_update_timer.start(1000)

    @pyqtSlot()
    def on_auto_update_timer(self):
        """Method called by the auto_update_timer.

            Updates the graphs at regular intervals.
            display_on_upcoming_passes doppler shifts.
            """

        self.draw_upcoming_passes()

        up_positions = []
        dynamic_lines = []

        selected_satellite = self.comboBoxSelectSatelllite.itemData(
            self.comboBoxSelectSatelllite.currentIndex())
        if selected_satellite is None:
            return  # Will be None if combo box is cleared

        for v in self.satellites_filtered_by_check_boxes():
            sat = v['Satellite']
            calc_time = ts.now().tt
            alt, az, slant_velocity = self.get_alt_azimuth(calc_time, sat)

            if alt.degrees > 0:
                up_positions.append((alt.degrees, az.radians, 'grey', 8, f' {sat}'))  # append tuple
                if sat == selected_satellite:

                    doppler_shift_2m = -slant_velocity / 300000 * 145.9e6
                    doppler_shift_100 = -slant_velocity / 300000 * 100e6  # 145.9e6

                    # print(slant_velocity, doppler_shift_100)
                    doppler_shift_70cm = -slant_velocity / 300000 * 436.5e6

                    selected_doppler_shift = -slant_velocity / 300000 * float(
                        self.selected_frequencies.currentText()) * 1e6

                    up_positions.append((alt.degrees, az.radians, 'black', 8,
                                         f' {sat}: 2: {doppler_shift_2m:+0.0f}, 70: {doppler_shift_70cm:+0.0f} Hz '))

                    self.doppler.setText(f'{selected_doppler_shift:+0.0f} Hz')

        if self.lines:
            dynamic_lines.append(self.lines[0])

        for up in up_positions:
            dynamic_lines.append([up])

            self.current_pass_graph.draw(*dynamic_lines)

        self.update()

    @pyqtSlot()
    def on_clock_update(self):
        """Method called by the clock_update_timer.

            Updates the status bar at regular intervals.
            """

        now = QDateTime.currentDateTime().toString()
        now_utc = QDateTime.currentDateTimeUtc().toString()
        self.statusBar().showMessage(f'{now} Local, {now_utc}')

    def create_pass_line(self, sat, rise_time, setting_time, interval, colour, text_every_point=10):
        """Create an orbit transit line of a satellite pass
            that can be plotted on a Polar graph.

            satellite -> an  artificial satellite name : string
            rise_time -> a ts, the time of rise of satellite above the horizon.
            setting_time -> a ts, the time of setting of satellite below the horizon.
            interval -> Time interval between points, in seconds.
            colour -> colour of the line and texts.
            text_every_point -> number of points between texts being added to the points.
                The last point also has a text.
                If zero, no texts are added.

            """

        pass_line = []

        point_number = 0

        calc_time = rise_time.tt

        while calc_time < setting_time.tt:
            text_field = ''

            alt, az, velocity = self.get_alt_azimuth(calc_time, sat)

            # See if point should have a text field
            calendar = ts.tt_jd(calc_time).tt_calendar()
            if text_every_point and (point_number % text_every_point == 0):
                text_field = f' {calendar[3]:02d}:{calendar[4]:02d}:{calendar[5]:02.0f}'

            pass_line.append([alt.degrees, az.radians, colour, 4, text_field])

            last_time = calc_time
            calc_time += JULIAN_SEC * interval

            point_number += 1

        if text_every_point and pass_line:  # pass_line must not be empty
            pass_line[-1][4] = f' {calendar[3]:02d}:{calendar[4]:02d}:{calendar[5]:02.0f}'  # Last point has text field

        return pass_line

    def get_alt_azimuth(self, calc_time, satellite_name):


        try:
            satellite_number = self.satellites[satellite_name]['Number']
            satellite = self.by_number[int(satellite_number)]
        except ValueError:
            return Angle(degrees=0), Angle(degrees=0), 0

        difference = satellite - home
        topocentric = difference.at(ts.tt_jd(calc_time))
        pos = topocentric.position.km
        alt, az, distance = topocentric.altaz()
        velocity = topocentric.velocity.km_per_s

        d = np.dot(velocity, pos) / np.linalg.norm(pos)  # slant velocity km/sec

        return alt, az, d

    def get_next_passes(self, satellite_name, number_of_passes):

        """Returns: event_list: list"""

        event_list = []

        now_ts = ts.now()
        try:
            satellite_number = self.satellites[satellite_name]['Number']
            satellite = self.by_number[int(satellite_number)]

            end_ts = ts.tt_jd(now_ts.tt + 1)

            event_times_ts, events = satellite.find_events(home, now_ts, end_ts, altitude_degrees=0.0)

            passes = 0

            for ti, event in zip(event_times_ts, events):
                if passes >= number_of_passes:
                    break
                event_name = ('rise', 'transit', 'set')[event]
                event_list.append((ti, event_name))
                if event_name == 'set':
                    passes += 1
        except ValueError:
            event_list = []

        return event_list

    def draw_next_passes_for_selected_satellite(self):
        """Draws the next passes for the selected satellite on the polar graphs."""

        satellite_name = self.comboBoxSelectSatelllite.itemData(self.comboBoxSelectSatelllite.currentIndex())
        if satellite_name is None:
            return  # Will be None if combobox is clear (at start up)

        pass_list = self.get_next_passes(satellite_name, self.spinBoxNextPasses.value())

        if not pass_list:
            return

        plot_colours = ('firebrick', 'sandybrown', 'olive', 'darkgreen', 'purple', 'blue')

        self.lines = []
        self.next_pass_polar_lines = []

        if pass_list[0][1] != 'rise':
            # create rise time as now
            now_ts = ts.now()
            pass_list.insert(0, (now_ts, 'rise'))

        p = 0
        for pass_event in pass_list:

            if pass_event[1] == 'rise':
                rise_ts = pass_event[0]
            elif pass_event[1] == 'set':
                set_ts = pass_event[0]

                if p == 0:
                    self.lines.append(self.create_pass_line(
                        satellite_name, rise_ts, set_ts, 30, plot_colours[0], 4)[:])

                self.next_pass_polar_lines.append(
                    self.create_pass_line(
                        satellite_name, rise_ts, set_ts, 30, plot_colours[p % len(plot_colours)], 4)[:])
                p += 1

        self.current_pass_graph.draw(*self.lines)

        self.next_passes_graph.draw(*self.next_pass_polar_lines)

        self.update()

    def draw_upcoming_passes(self):
        """Draws the next pass for the selected satellites
            on the upcoming passes graph."""

        transit_list = self.transit_list_sorted_by_time()

        self.next_pass_lines = []

        for transit in transit_list:
            now = ts.now().tt  # Julian
            if  not transit[0]:
                transit[0] = now

            if transit[1]:
                alt, az, velocity = self.get_alt_azimuth(transit[1], transit[3])
            else:
                alt, az, velocity = self.get_alt_azimuth(now, transit[3])

            rise_delta = transit[0] - now
            set_delta = transit[2] - now

            if (set_delta* 24) < self.hours_to_show:
                self.next_pass_lines.append([(rise_delta * 24., alt.degrees, 'purple', 6),  # Start point
                                     (set_delta * 24., alt.degrees, 'purple', 6, ' ' + transit[3])]
                                    )

        # Tell the MainApp to plot the lines on the graphs
        # A list of line lists of point tuples
        self.upcoming_passes_graph.draw(*self.next_pass_lines)

        self.update()


    def display_next_passes_for_selected_satellite(self):
        """Displays the next passes for the selected satellite on the
            text display_on_upcoming_passes."""

        satellite_name = self.comboBoxSelectSatelllite.itemData(
            self.comboBoxSelectSatelllite.currentIndex())

        if satellite_name is None:
            return  # Will be None if combo box is cleared

        self.display_on_selected_satellite_passes(f'Time Zone: {"Local" if LOCALTIME else "UTC"}')

        self.display_on_selected_satellite_passes(f'Next 10 passes for satellite: {satellite_name}', colour='purple')
        self.display_on_selected_satellite_passes()

        transit_list = []

        pass_list = self.get_next_passes(satellite_name, 10)

        pass_info = [0, 0, 0, satellite_name]
        for pass_event in pass_list:
            if pass_event[1] == 'rise':
                pass_info[0] = pass_event[0].tt
            elif pass_event[1] == 'transit':
                pass_info[1] = pass_event[0].tt
            elif pass_event[1] == 'set':
                pass_info[2] = pass_event[0].tt
                transit_list.append(pass_info)
                pass_info = [0, 0, 0, satellite_name]

        transit_list.sort()

        for transit in transit_list:
            if transit[0]:
                rise_time = ts.tt_jd(transit[0]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[0], transit[3])

                self.display_on_selected_satellite_passes(f'Rise    : {rise_time} az: {az.degrees:5.1f}°', colour='darkgreen')

            if transit[1]:
                transit_time = ts.tt_jd(transit[1]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[1], transit[3])

                self.display_on_selected_satellite_passes(f'Transit : {transit_time} az: {az.degrees:5.1f}° alt: {alt.degrees:4.1f}°', colour='darkgreen')

            if transit[2]:
                set_time = ts.tt_jd(transit[2]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[2], transit[3])

                self.display_on_selected_satellite_passes(f'Set     : {set_time} az: {az.degrees:5.1f}°', colour='darkgreen')

            self.display_on_selected_satellite_passes()

        self.display_on_selected_satellite_passes('Listing finished!', colour='red')

        self.scroll_selected_satellite_passes_display(0)



    def load_tles(self):
        """Get all the amateur satellite TLEs from celestrak and
            save the TLEs in text file `satellites.tle`.
            """

        # Get the satelliteBodyObjects from the TLEs file
        stations_url = 'http://celestrak.com/NORAD/elements/amateur.txt'
        self.satellite_body_objects = load.tle_file(stations_url)

        QMessageBox.information(self, "Ephemera",
                                'TLEs Downloaded!',
                                QMessageBox.Ok)

    def display_upcoming_passes(self):
        """Displays the upcoming passes for the selected satellites
            using `self.display_on_upcoming_passes()`.
            """

        transit_list = self.transit_list_sorted_by_time()

        self.display_on_upcoming_passes(f'Time Zone: {"Local" if LOCALTIME else "UTC"}')
        for transit in transit_list:
            self.display_on_upcoming_passes(f'Pass for satellite: {transit[3]}', colour='purple')
            if transit[0]:
                rise_time = ts.tt_jd(transit[0]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[0], transit[3])
                self.display_on_upcoming_passes(f'Rise    : {rise_time} az: {az.degrees:5.1f}°', colour='darkgreen')

            if transit[1]:
                transit_time = ts.tt_jd(transit[1]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[1], transit[3])
                self.display_on_upcoming_passes(f'Transit : {transit_time} az: {az.degrees:5.1f}° alt: {alt.degrees:4.1f}°', colour='darkgreen')

            if transit[2]:
                set_time = ts.tt_jd(transit[2]).utc_iso(' ')
                alt, az, velocity = self.get_alt_azimuth(transit[2], transit[3])
                self.display_on_upcoming_passes(f'Set     : {set_time} az: {az.degrees:5.1f}°', colour='darkgreen')

            self.display_on_upcoming_passes()

        self.display_on_upcoming_passes('Listing finished!', colour='red')
        self.scroll_upcoming_passes_display(0)

    def closeEvent(self, event):
        """Extends inherited QMainWindow closeEvent.

            Do any cleanup actions before the application closes.

            Saves the application geometry.
            Accepts the event which closes the application.
            """

        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()
        super().closeEvent(event)

    def resizeEvent(self, event):
        """Extends inherited QMainWindow resize event.

            re-draws the graph to fill the new scroller size."""

        self.settings.setValue("geometry", self.saveGeometry())

        self.update_graph_sizes()

        super().resizeEvent(event)

    def moveEvent(self, event):
        """Extends inherited QMainWindow move event."""

        self.settings.setValue("geometry", self.saveGeometry())

        super().moveEvent(event)

    def update_graph_sizes(self):
        """Re-draw the graphs at the new sizes."""

        if self.upcoming_passes_graph:
            # find the size that the graph will be re-drawn
            x_size = self.scrollArea.width() - 4
            y_size = self.scrollArea.height() - 4

            self.upcoming_passes_graph = reCreateGraph(self.upcoming_passes_graph, x_size, y_size)

        if self.next_passes_graph:
            # find the size that the graph will be re-drawn
            x_size = self.scrollAreaShowPasses.width() - 4
            y_size = self.scrollAreaShowPasses.height() - 4

            self.next_passes_graph = reCreateGraph(self.next_passes_graph, x_size, y_size)

        if self.current_pass_graph:
            # find the size that the graph will be re-drawn
            x_size = self.scrollAreaCurrentPass.width() - 4
            y_size = self.scrollAreaCurrentPass.height() - 4

            self.current_pass_graph = reCreateGraph(self.current_pass_graph, x_size, y_size)

    def draw_graphs(self):
        """Draw the graphs on the MainApp ScrollAreas
            when new graphs needs to be created.
            """

        # find the size that the Graph will be drawn
        xSize = self.scrollArea.width() - 4
        ySize = self.scrollArea.height() - 4

        if not self.upcoming_passes_graph:
            # create the Graph
            self.upcoming_passes_graph = Graph(self.labelGraph,
                                               0, self.hours_to_show,
                                               0, 100,
                                               xgrids=6, ygrids=10,
                                               size_x=xSize, size_y=ySize,
                                               text_pixel_size=22,
                                               background=QColor(240, 250, 255))

            self.upcoming_passes_graph.set_grid_label_format('{:0.0f}h', '{:0.0f}°')

            self.upcoming_passes_graph.add_text('          Upcoming Satellites', 0, 95, 'purple', True)
            self.upcoming_passes_graph.add_text_by_proportion('Hours from now', 0.71, 0.02, 'blue', True)
            self.upcoming_passes_graph.add_text('          Maximum Altitude', 0, 90, 'red', True)

            # Call the draw method to show the grid, text and any lines
            self.upcoming_passes_graph.draw()

        # create the Polar graph
        # find the size that the Graph will be drawn
        xSize = self.scrollAreaShowPasses.width() - 4
        ySize = self.scrollAreaShowPasses.height() - 4

        if not self.next_passes_graph:
            # create the graph
            self.next_passes_graph = Polar(self.labelPolarShowPasses,
                                           size_x=xSize, size_y=ySize,
                                           text_pixel_size=20,
                                           background=QColor('mintcream'))

            self.next_passes_graph.set_grid_label_format('{:0.0f}°', '{:0.0f}°')

            self.next_passes_graph.add_polar_text('Azimuth', 0, math.radians(45), 'red', True)
            self.next_passes_graph.add_polar_text('Altitude', 80, math.radians(90), 'blue', True)
            self.next_passes_graph.add_text_by_proportion(' Next Passes', 0, .95, 'purple', True)

            # Call the draw method to show the grid, text and any lines
            self.next_passes_graph.draw()

        # create the Polar graph
        # find the size that the Graph will be drawn
        xSize = self.scrollAreaCurrentPass.width() - 4
        ySize = self.scrollAreaCurrentPass.height() - 4

        if not self.current_pass_graph:
            # create the graph
            self.current_pass_graph = Polar(self.labelPolarCurrentPass,
                                            size_x=xSize, size_y=ySize,
                                            text_pixel_size=20,
                                            background=QColor('#FFFEFE'))

            self.current_pass_graph.set_grid_label_format('{:0.0f}°', '{:0.0f}°')

            self.current_pass_graph.add_polar_text('Azimuth', 0, math.radians(45), 'red', True)
            self.current_pass_graph.add_polar_text('Altitude', 80, math.radians(90), 'blue', True)
            self.current_pass_graph.add_text_by_proportion(' Next Pass', 0, .95, 'purple', True)

            # Call the draw method to show the grid, text and any lines
            self.current_pass_graph.draw()

    @pyqtSlot(int, int)
    def on_splitterV_splitterMoved(self, pos, index):
        """Slot triggered when the splitter is moved.

            re-draws the graph to fill the new scroller size,
            saves the new position."""

        self.splitter_v_position = pos

        self.update_graph_sizes()

        self.settings.setValue('splitterVposn', self.splitter_v_position)

    @pyqtSlot(int, int)
    def on_splitterH_splitterMoved(self, pos, index):
        """Slot triggered when the splitter is moved.

            re-draws the graph to fill the new scroller size,
            saves the new positions."""

        self.update_graph_sizes()

        self.settings.setValue(f'splitterHposn{index}', pos)

    # --- Text Edit display_on_upcoming_passes methods, not normally modified:

    def display_on_upcoming_passes(self, *items, colour='black'):
        """Display the items on the text edit control using their normal
            string representations on a single line.
            A space is added between the items.
            Any trailing spaces are removed.

            If the colour is not given the default
            colour ('black') is used. The colour, if used, must be given
            as a keyword argument.

            The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.
            """

        display_string = ''
        for item in items:
            display_string += '{} '.format(item)

        tEdit = self.textEdit
        append_text_to_text_edit(tEdit, display_string.rstrip(' '), colour)

    def clear_upcoming_passes_display(self):

        self.textEdit.clear()

    def scroll_upcoming_passes_display(self, scroll_position=0):

        self.textEdit.verticalScrollBar().setValue(scroll_position)

    def display_on_selected_satellite_passes(self, *items, colour='black'):
        """Display the items on the text edit control using their normal
            string representations on a single line.
            A space is added between the items.
            Any trailing spaces are removed.

            If the colour is not given the default
            colour ('black') is used. The colour, if used, must be given
            as a keyword argument.

            The colour may be be any string that may be
            passed to QColor, such as a name like 'red' or
            a hex value such as '#F0F0F0'.
            """

        display_string = ''
        for item in items:
            display_string += '{} '.format(item)

        tEdit = self.textEditSelectedSatellite
        append_text_to_text_edit(tEdit, display_string.rstrip(' '), colour)

    def clear_selected_satellite_passes_display(self):

        self.textEditSelectedSatellite.clear()

    def scroll_selected_satellite_passes_display(self, scroll_position=0):

        self.textEditSelectedSatellite.verticalScrollBar().setValue(scroll_position)

    def debug(self, *items):
        """Display the items on the text edit control using their normal
            string representations.

            The colour is fixed at orange.

            The display_on_upcoming_passes may be disabled once the program has
            been debugged by changing self.showDebug.
            """

        if self.showDebug:
            self.display_on_upcoming_passes(*items, colour='orange')


def file_lines(filename):
    """Generator: yield the next line in the file.

        Whitespace is stripped from the line"""

    with open(filename, 'r') as f:
        for line in f:
            yield line.strip()


def truncate(number, places=0) -> str:
    """Convert `number` to a string with `places` decimal places."""

    if not isinstance(places, int):
        raise ValueError("Decimal places must be an integer.")
    if places < 0:
        raise ValueError("Decimal places must not be negative.")

    # If you want to truncate to 0 decimal places, just use int(number)
    if places == 0:
        return str(int(number))

    with localcontext() as context:
        context.rounding = ROUND_DOWN
        exponent = Decimal(str(10 ** - places))
        return Decimal(str(number)).quantize(exponent).to_eng_string()


def eDate(ephemDate, local=None):
    """Return the date/time in local or UTC."""

    if local is None:
        try:  # See if global LOCALTIME is defined
            local = LOCALTIME
        except NameError:
            pass
    if local:
        return ephem.localtime(ephemDate)
    else:
        return ephemDate.datetime()


def eDelta(delta):
    """Convert to a date/time from 00:00:00 1900/1/1."""

    return ephem.Date(delta + 12 * ephem.hour)


def append_text_to_text_edit(tEdit, txt, colour='black'):
    """Appends the text in txt to the end of the tEdit, a QTextEdit.

        The text colour is set by the parameter colour.
        The text is added as a new line in an html table."""

    # convert spaces to html escape characters
    text = txt.replace(' ', '&nbsp;')

    # build the html string
    html = '<table cellspacing=0 width=100%><tr><td style= "color:'
    html += colour
    html += '">'
    html += text
    html += '</td></tr></table>'

    # get the cursor from the tEdit
    cursor = tEdit.textCursor()

    # position at end of line
    cursor.movePosition(cursor.End)
    pos = cursor.position()

    # insert the text
    cursor.insertHtml(html)

    cursor.setPosition(pos, cursor.MoveAnchor)
    cursor.movePosition(cursor.End, cursor.KeepAnchor)
    cursor.clearSelection()

    # position so viewport scrolled to left
    cursor.movePosition(cursor.Up)
    cursor.movePosition(cursor.StartOfLine)
    tEdit.setTextCursor(cursor)
    tEdit.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainApp()
    sys.exit(app.exec_())
