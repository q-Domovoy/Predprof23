import sqlite3
import sys
import datetime

from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import requests
import numpy as np
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('MainWindow.ui', self)
        self.toTableButton.clicked.connect(self.to_table)
        self.exitButton.clicked.connect(self.exit)

    def to_table(self):
        self.hide()
        self.table = CompsTableWindow()
        self.table.show()

    def exit(self):
        sys.exit()


class CompsTableWindow(QMainWindow):
    def __init__(self):
        super(CompsTableWindow, self).__init__()
        uic.loadUi('CompetitionsTable.ui', self)
        self.addButton.clicked.connect(self.add_competition)
        self.deleteButton.clicked.connect(self.delete_competition)
        self.menuButton.clicked.connect(self.to_main_menu)
        self.toRacesButton.clicked.connect(self.view_competition)
        self.tableWidget.cellClicked.connect(self.cell_was_clicked)
        self.load()
        self.Competition = None

    def add_competition(self):
        new_comp_data = NewCompetitionDialog()
        if new_comp_data.exec():
            title = new_comp_data.title_line.text()
            date = new_comp_data.date_line.text()
            organizer = new_comp_data.organizer_line.text()
            place = new_comp_data.place_line.text()
            sqlite_connection = sqlite3.connect('./data/data.db')
            cursor = sqlite_connection.cursor()
            sqlite_insert = f'INSERT INTO competitions(comp_id, title, date, organizer, place) VALUES(?, ?, ?, ?, ?)'
            dataCopy = cursor.execute("select * from competitions").fetchall()
            if len(dataCopy) == 0:
                last_id = 1
            else:
                last_id = int(dataCopy[-1][0]) + 1
            cursor.execute(sqlite_insert, (last_id, title, date, organizer, place))
            sqlite_connection.commit()
            cursor.close()
            sqlite_connection.close()
            self.load()
        else:
            pass

    def delete_competition(self):
        if not (self.tableWidget.currentRow() + 1):
            self.label_selectRow.setText('Сначала выберите заезд!')
        else:
            self.label_selectRow.setText('')
            sqlite_connection = sqlite3.connect('./data/data.db')
            cursor = sqlite_connection.cursor()
            cursor.execute(f'DELETE FROM competitions WHERE comp_id="{self.Competition.id}"')
            for i in cursor.execute(f'SELECT race_id from races WHERE comp_id={self.Competition.id}').fetchall():
                cursor.execute(f'DROP table race_{i[0]}')
            cursor.execute(f'DELETE FROM races WHERE comp_id="{self.Competition.id}"')

            sqlite_connection.commit()
            cursor.close()
            sqlite_connection.close()
            self.load()

    def cell_was_clicked(self):
        a = self.tableWidget.item(self.tableWidget.currentRow(), 0)
        self.Competition = RacesTableWindow(int(a.text()))

    def view_competition(self):
        if not (self.tableWidget.currentRow() + 1) or self.Competition is None:
            self.label_selectRow.setText('Сначала выберите соревнование!')
        else:
            self.label_selectRow.setText('')
            self.Competition.show()
            self.hide()

    def to_main_menu(self):
        self.close()
        ex.show()

    def load(self):
        self.tableWidget.setRowCount(0)
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        cur.execute("SELECT * FROM competitions")
        rows = cur.fetchall()
        for row in rows:
            indx = rows.index(row)
            self.tableWidget.insertRow(indx)
            self.tableWidget.setItem(indx, 0, QTableWidgetItem(str(row[0])))
            self.tableWidget.setItem(indx, 1, QTableWidgetItem(str(row[1])))
            self.tableWidget.setItem(indx, 2, QTableWidgetItem(str(row[2])))
            self.tableWidget.setItem(indx, 3, QTableWidgetItem(str(row[3])))
            self.tableWidget.setItem(indx, 4, QTableWidgetItem(str(row[4])))
        cur.close()
        sqlite_connection.close()


class NewCompetitionDialog(QDialog):
    def __init__(self):
        super(NewCompetitionDialog, self).__init__()
        uic.loadUi('NewCompetition.ui', self)


class RacesTableWindow(QMainWindow):
    def __init__(self, comp_id):
        super(RacesTableWindow, self).__init__()
        uic.loadUi('RacesTable.ui', self)
        self.id = comp_id
        self.load()
        self.StartRace = None

        #graphWidget:
        self.graphWidget = pg.PlotWidget()
        self.verticalLayout.addWidget(self.graphWidget)
        self.graphWidget.setBackground('w')
        self.graphWidget.setTitle("Угол", color="gray", size="15pt")
        styles = {'color': 'b', 'font-size': '10px'}
        self.graphWidget.setLabel('left', 'Угол (°)', **styles)
        self.graphWidget.setLabel('bottom', 'Время (с)', **styles)
        self.graphWidget.setYRange(-200, 200)
        self.graphWidget.setXRange(0, 30)

        #button clicks:
        self.MenuButton.clicked.connect(self.to_competitions)
        self.NewRaceButton.clicked.connect(self.create_new_race)
        self.OpenDataButton.clicked.connect(self.view_race)
        self.DeleteButton.clicked.connect(self.delete)
        self.tableWidget.cellClicked.connect(self.cell_was_clicked)

    def plot(self, x, y, plotname, color):
        pen = pg.mkPen(color=color)
        self.graphWidget.plot(x, y, name=plotname, pen=pen)

    def cell_was_clicked(self):
        self.graphWidget.clear()
        self.StartRace = Race(int(self.tableWidget.item(self.tableWidget.currentRow(), 0).text()))
        sqlite_connection = sqlite3.connect('./data/data.db')
        cursor = sqlite_connection.cursor()
        x = list(float(_[0]) for _ in cursor.execute(f'SELECT time FROM race_{self.StartRace.id}').fetchall())
        if self.StartRace.isFinished:
            y1 = list(float(_[0]) for _ in cursor.execute(f'SELECT pilot1 FROM race_{self.StartRace.id}').fetchall())
            self.plot(x, y1, "Pilot1", 'r')
            if self.StartRace.num_pilots == 2:
                y2 = list(float(_[0]) for _ in cursor.execute(f'SELECT pilot2 FROM race_{self.StartRace.id}').fetchall())
                self.plot(x, y2, "Pilot2", 'b')
        elif self.StartRace.isFinished1:
            y1 = list(float(_[0]) for _ in cursor.execute(f'SELECT pilot1 FROM race_{self.StartRace.id}').fetchall())
            self.plot(x, y1, "Pilot1", 'r')
        elif self.StartRace.isFinished2:
            y2 = list(float(_[0]) for _ in cursor.execute(f'SELECT pilot2 FROM race_{self.StartRace.id}').fetchall())
            self.plot(x, y2, "Pilot2", 'b')

        sqlite_connection.commit()
        cursor.close()
        sqlite_connection.close()

    def to_competitions(self):
        self.close()
        ex.table.show()

    def delete(self):
        if not (self.tableWidget.currentRow() + 1):
            self.label_selectRow.setText('Сначала выберите заезд!')
        else:
            self.label_selectRow.setText('')
            sqlite_connection = sqlite3.connect('./data/data.db')
            cursor = sqlite_connection.cursor()
            cursor.execute(f'DELETE FROM races WHERE race_id={self.StartRace.id} AND comp_id={self.id}')
            cursor.execute(f'DROP TABLE race_{self.StartRace.id}')
            sqlite_connection.commit()
            cursor.close()
            sqlite_connection.close()
            self.load()

    def create_new_race(self):
        new_race_data = NewRaceDialog()
        if new_race_data.exec():
            type = new_race_data.type_line.text()
            pilot1_num = new_race_data.pilot1_line.text()
            pilot2_num = new_race_data.pilot2_line.text()
            sqlite_connection = sqlite3.connect('./data/data.db')
            cursor = sqlite_connection.cursor()
            sqlite_insert = 'INSERT INTO races(race_id, comp_id, type, pilots_numbers, isFinished, start_time, end_time) VALUES(?, ?, ?, ?, ?, ?, ?)'
            dataCopy = cursor.execute("select * from races").fetchall()
            if len(dataCopy) == 0:
                last_id = 1
            else:
                last_id = int(dataCopy[-1][0]) + 1
            if pilot2_num == '':
                cursor.execute(sqlite_insert, (last_id, self.id, type, pilot1_num, "False", None, None))
            else:
                cursor.execute(sqlite_insert, (last_id, self.id, type, ', '.join([pilot1_num, pilot2_num]), "False", None, None))
            cursor.execute(f'CREATE TABLE race_{last_id}(time REAL, pilot1, pilot2)')
            sqlite_connection.commit()
            cursor.close()
            sqlite_connection.close()
            self.load()
        else:
            pass

    def view_race(self):
        if not (self.tableWidget.currentRow() + 1) or self.StartRace is None:
            self.label_selectRow.setText('Сначала выберите заезд!')
        else:
            self.label_selectRow.setText('')
            self.hide()
            self.StartRace.show()
            self.StartRace.load()


    def load(self):
        self.tableWidget.setRowCount(0)
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        cur.execute(f"SELECT * FROM races WHERE comp_id={self.id}")
        rows = cur.fetchall()
        for row in rows:
            indx = rows.index(row)
            self.tableWidget.insertRow(indx)
            self.tableWidget.setItem(indx, 0, QTableWidgetItem(str(row[0])))
            self.tableWidget.setItem(indx, 1, QTableWidgetItem(str(row[2])))
            self.tableWidget.setItem(indx, 2, QTableWidgetItem(str(row[3])))
        cur.close()
        sqlite_connection.close()


class NewRaceDialog(QDialog):
    def __init__(self):
        super(NewRaceDialog, self).__init__()
        uic.loadUi('NewRace.ui', self)


class Race(QMainWindow):
    def __init__(self, race_id):
        super(Race, self).__init__()
        uic.loadUi('RaceView.ui', self)
        self.id = race_id
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()

        a = cur.execute(f'SELECT pilots_numbers FROM races WHERE race_id={self.id}').fetchone()[0].split(', ')
        self.pilot1_num = a[0]
        if len(a) == 1:
            self.num_pilots = 1
            self.pilot2Button.setEnabled(False)
        else:
            self.num_pilots = 2
            self.pilot2_num = a[1]
        self.pilot = 1

        #isFinished:
        if cur.execute(f'SELECT isFinished FROM races WHERE race_id={self.id} AND comp_id={ex.table.Competition.id}').fetchone()[0] == 'True':
            self.isFinished = True
        else:
            self.isFinished = False
        if self.isFinished:
            self.isStartedlabel.setText('Заезд завершён')
            self.startButton.setEnabled(False)
            self.tableViewButton.setEnabled(True)
            self.pilot2Button.setEnabled(False)
        else:
            self.startButton.setEnabled(True)
            self.tableViewButton.setEnabled(False)
            a = cur.execute(f'SELECT pilot1 FROM race_{self.id}').fetchone()
            b = cur.execute(f'SELECT pilot2 FROM race_{self.id}').fetchone()
            if a is None and b is None:
                self.isStartedlabel.setText('Заезд не начат')
                self.isFinished2 = False
                self.isFinished1 = False
            elif a[0] is None:
                self.isFinished1 = False
                self.isFinished2 = True
                self.isStartedlabel.setText(f'Заезд не начат для пилота {self.pilot1_num}')
            elif b[0] is None and self.num_pilots == 2:
                self.isFinished2 = False
                self.isFinished1 = True
                self.startButton.setEnabled(False)
                self.isStartedlabel.setText(f'Заезд не начат для пилота {self.pilot2_num}')
            else:
                self.isStartedlabel.setText('Заезд не начат')
                self.isFinished2 = False
                self.isFinished1 = False


        #buttons:
        self.pilot1Button.setEnabled(False)
        self.backButton.clicked.connect(self.back)
        self.startButton.clicked.connect(self.start)
        self.tableViewButton.clicked.connect(self.table_view)
        self.pilot1Button.clicked.connect(self.change_to_pilot1)
        self.pilot2Button.clicked.connect(self.change_to_pilot2)

        #graphWidget:
        self.graphWidget = pg.PlotWidget()
        self.layout.addWidget(self.graphWidget)
        self.graphWidget.setBackground('w')
        self.graphWidget.setTitle("Угол", color="gray", size="15pt")
        styles = {'color': 'b', 'font-size': '10px'}
        self.graphWidget.setLabel('left', 'Угол (°)', **styles)
        self.graphWidget.setLabel('bottom', 'Время (с)', **styles)
        self.graphWidget.setYRange(-200, 200)
        self.graphWidget.setXRange(0, 30)
        self.pen1 = pg.mkPen(color=(255, 0, 0))
        self.pen2 = pg.mkPen(color=(0, 0, 255))



        sqlite_connection.commit()
        cur.close()
        sqlite_connection.close()

    def table_view(self):
        self.hide()
        self.table_v = TableView()
        self.table_v.show()
        self.table_v.load()

    def plot(self, x, y, plotname, color):
        pen = pg.mkPen(color=color)
        self.graphWidget.plot(x, y, name=plotname, pen=pen)

    def load(self):
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        if self.isFinished:
            self.x = list(float(_[0]) for _ in cur.execute(f'SELECT time FROM race_{str(self.id)}').fetchall())
            self.y1 = list(float(_[0]) for _ in cur.execute(f'SELECT pilot1 FROM race_{str(self.id)}').fetchall())
            self.plot(self.x, self.y1, "Pilot1", 'r')
            if self.num_pilots == 2:
                self.y2 = list(float(_[0]) for _ in cur.execute(f'SELECT pilot2 FROM race_{str(self.id)}').fetchall())
                self.plot(self.x, self.y2, "Pilot2", 'b')
        elif self.isFinished1:
            self.x = list(float(_[0]) for _ in cur.execute(f'SELECT time FROM race_{str(self.id)}').fetchall())
            self.y1 = list(float(_[0]) for _ in cur.execute(f'SELECT pilot1 FROM race_{str(self.id)}').fetchall())
            self.plot(self.x, self.y1, "Pilot1", 'r')
        elif self.isFinished2:
            self.x = list(float(_[0]) for _ in cur.execute(f'SELECT time FROM race_{str(self.id)}').fetchall())
            self.y2 = list(float(_[0]) for _ in cur.execute(f'SELECT pilot2 FROM race_{str(self.id)}').fetchall())
            self.plot(self.x, self.y2, "Pilot2", 'b')
        cur.close()
        sqlite_connection.close()


    def save(self):
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        self.x = [round(i, 1) for i in np.arange(0, 30.1, 0.1)]
        finish1, finish2 = False, False
        if self.pilot == 1:
            if self.num_pilots == 2 and self.isFinished2:
                last_data2 = cur.execute(f'SELECT * FROM race_{self.id}').fetchall()
                finish2 = True
                last_time = [_[0] for _ in last_data2]
                last_pilot2 = [_[2] for _ in last_data2]
                cur.execute(f'DELETE FROM race_{self.id}')
                sqlite_connection.commit()
            self.y1 = self.y1[::3]
            a = float(self.y1[0])
            self.y1 = self.y1[1:]
            self.y1 = self.y1[:-1]
            self.y1 = [str((float(i) - a) - ((float(i) - a) % 5)) for i in self.y1]
            self.y1.insert(0, '0')
            ln = len(self.y1)
            y1_up = [self.y1[-1]] * (301 - ln)
            if ln < 301:
                self.y1.extend(y1_up)
            elif ln > 301:
                self.y1 = self.y1[:301]
            self.y1.append(self.y1[-1])


            cur.execute('UPDATE races SET end_time=? WHERE race_id=?', (str(datetime.datetime.now().isoformat(sep=' ')).split(' ')[1], self.id))
            sqlite_connection.commit()
        else:
            if self.num_pilots == 2 and self.isFinished1:
                last_data1 = cur.execute(f'SELECT * FROM race_{self.id}').fetchall()
                finish1 = True
                last_time = [_[0] for _ in last_data1]
                last_pilot1 = [_[1] for _ in last_data1]
                cur.execute(f'DELETE FROM race_{self.id}')
                sqlite_connection.commit()
            else:
                cur.execute('UPDATE races SET end_time=? WHERE race_id=?', (str(datetime.datetime.now().isoformat(sep=' ')).split(' ')[1], self.id))
                sqlite_connection.commit()
            self.y2 = self.y2[::3]
            a = float(self.y2[0])
            self.y2 = self.y2[1:]
            self.y2 = self.y2[:-1]
            self.y2 = [str((float(i) - a) - ((float(i) - a) % 5)) for i in self.y2]
            self.y2.insert(0, '0')
            ln = len(self.y2)
            y2_up = [self.y2[-1]] * (301 - ln)
            if ln < 301:
                self.y2.extend(y2_up)
            elif ln > 301:
                self.y2 = self.y2[:301]
            self.y2.append(self.y2[-1])



        for i in range(301):
            if self.pilot == 1:
                if finish2:
                    cur.execute(f'INSERT OR IGNORE INTO race_{self.id} (time, pilot1, pilot2) VALUES(?, ?, ?)',
                                (last_time[i], self.y1[i], last_pilot2[i]))
                else:
                    cur.execute(f'INSERT OR IGNORE INTO race_{self.id} (time, pilot1, pilot2) VALUES(?, ?, ?)', (self.x[i], self.y1[i], None))
            else:
                if finish1:
                    cur.execute(f'INSERT OR IGNORE INTO race_{self.id} (time, pilot1, pilot2) VALUES(?, ?, ?)',
                                (last_time[i], last_pilot1[i], self.y2[i]))
                else:
                    cur.execute(f'INSERT OR IGNORE INTO race_{self.id} (time, pilot1, pilot2) VALUES(?, ?, ?)', (self.x[i], None, self.y2[i]))
        if self.num_pilots == 1:
            self.isFinished = True
            cur.execute(f'UPDATE races SET isFinished="True" WHERE race_id ={self.id}')
        elif self.num_pilots == 2:
            if self.pilot == 1 and not self.isFinished2:
                self.isFinished1 = True
            elif self.pilot == 2 and not self.isFinished1:
                self.isFinished2 = True
            else:
                self.isFinished = True
                cur.execute(f'UPDATE races SET isFinished="True" WHERE race_id ={self.id}')

        sqlite_connection.commit()
        cur.close()
        sqlite_connection.close()
        self.tableViewButton.setEnabled(True)

    def back(self):
        self.close()
        ex.table.Competition.show()

    def change_to_pilot1(self):
        self.pilot1Button.setEnabled(False)
        self.pilot = 1
        if not self.isFinished1:
            self.startButton.setEnabled(True)
        if self.isFinished2:
            self.pilot2Button.setEnabled(False)
        else:
            self.pilot2Button.setEnabled(True)

    def change_to_pilot2(self):
        self.pilot2Button.setEnabled(False)
        self.pilot = 2
        if not self.isFinished2:
            self.startButton.setEnabled(True)
        if self.isFinished1:
            self.pilot1Button.setEnabled(False)
        else:
            self.pilot1Button.setEnabled(True)

    def start(self):
        url = 'http://esp8266.local/start'
        req = requests.get(url)
        if req:
            self.isStartedlabel.setText(f'Заезд начался...')
        self.pilot1Button.setEnabled(False)
        self.pilot2Button.setEnabled(False)
        self.startButton.setEnabled(False)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.finish)
        self.timer.start(30000)
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        now = datetime.datetime.now()
        now_aware = now.astimezone()
        if not self.isFinished1 and not self.isFinished2:
            cur.execute('UPDATE races SET start_time=? WHERE race_id=?', (str(datetime.datetime.now().isoformat(sep=' ')).split(' ')[1], self.id))
        sqlite_connection.commit()
        cur.close()
        sqlite_connection.close()

    def finish(self):
        url = 'http://esp8266.local/download'
        req = requests.get(url)
        if req:
            if self.pilot == 1:
                self.y1 = req.text.split(';\n')
            else:
                self.y2 = req.text.split(';\n')
        if self.pilot == 2:
            self.pilot1Button.setEnabled(True)
        if self.pilot == 1:
            self.pilot2Button.setEnabled(True)
        self.isStartedlabel.setText('Заезд завершён')
        self.save()
        self.load()
        self.startButton.setEnabled(False)



class TableView(QMainWindow):
    def __init__(self):
        super(TableView, self).__init__()
        uic.loadUi('TableViewRace.ui', self)
        self.MenuButton.clicked.connect(self.menu)
        self.toGraphButton.clicked.connect(self.graph_view)
        self.toTableButton.clicked.connect(self.to_table)

        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        r_type = cur.execute(f"SELECT type FROM races WHERE race_id={ex.table.Competition.StartRace.id}").fetchone()[0]
        self.type_label.setText(f'Тип заезда: {r_type}')
        pilot1 = cur.execute(f"SELECT pilots_numbers FROM races WHERE race_id={ex.table.Competition.StartRace.id}").fetchone()[0].split(', ')[0]
        self.tableWidget.horizontalHeaderItem(1).setText(f'Пилот {pilot1}')
        if ex.table.Competition.StartRace.num_pilots == 2:
            pilot2 = cur.execute(f"SELECT pilots_numbers FROM races WHERE race_id={ex.table.Competition.StartRace.id}").fetchone()[0].split(', ')[1]
            self.tableWidget.horizontalHeaderItem(2).setText(f'Пилот {pilot2}')
        else:
            self.tableWidget.horizontalHeaderItem(2).setText('Нет')
        sql_sel_start = cur.execute(f'SELECT start_time FROM races WHERE race_id={ex.table.Competition.StartRace.id}').fetchone()[0]
        sql_sel_end = cur.execute(f'SELECT end_time FROM races WHERE race_id={ex.table.Competition.StartRace.id}').fetchone()[0]

        self.start_time_label.setText(f'''Время начала заезда:
{sql_sel_start}''')
        self.end_time_label.setText(f'''Время окончания заезда:
{sql_sel_end}''')
        cur.close()
        sqlite_connection.close()

    def load(self):
        self.tableWidget.setRowCount(0)
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        cur.execute(f"SELECT * FROM race_{ex.table.Competition.StartRace.id}")
        rows = cur.fetchall()
        for row in rows:
            indx = rows.index(row)
            self.tableWidget.insertRow(indx)
            self.tableWidget.setItem(indx, 0, QTableWidgetItem(str(row[0])))
            self.tableWidget.setItem(indx, 1, QTableWidgetItem(str(row[1])))
            self.tableWidget.setItem(indx, 2, QTableWidgetItem(str(row[2])))
        cur.close()
        sqlite_connection.close()

    def menu(self):
        self.close()
        ex.table.show()

    def graph_view(self):
        self.close()
        ex.table.Competition.StartRace.show()

    def to_table(self):
        self.close()
        ex.table.Competition.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not os.path.isfile('./data/data.db'):
        os.mkdir('./data')
        os.path.join('./data', 'data.db')
        sqlite_connection = sqlite3.connect('./data/data.db')
        cur = sqlite_connection.cursor()
        cur.execute('''CREATE TABLE competitions (
    comp_id   INTEGER,
    title     TEXT,
    date,
    organizer TEXT,
    place     TEXT
)''')
        cur.execute('''CREATE TABLE races (
    race_id        INTEGER,
    comp_id        INTEGER,
    type           TEXT,
    pilots_numbers TEXT,
    isFinished     TEXT,
    start_time     TEXT,
    end_time       TEXT
)''')
        sqlite_connection.commit()
        cur.close()
        sqlite_connection.close()
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())
