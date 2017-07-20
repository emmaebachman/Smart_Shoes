import time
import serial
import threading
import math


# remember mpu data is in radians
class BLEInterface:
    def __init__(self, port='COM3', ):
        self.input_ser = serial.Serial(baudrate=57600)  # creates a serial port
        self.input_ser.port = port  # assigns a port
        self.input_ser.timeout = 0  # makes things not break
        self.input_ser.open()  # opens the port
        self.read_rate = 20000  # number of Hz that the MPU is running at
        self.line_frag = ""  # hopefully temporary, stores lost pieces of line

    def basic_write(self, message):  # actually sends a command to the BLE
        self.input_ser.write((message + '\r').encode())  # formats the command to prevent errors

    def send_message(self, message):  # simplifies sending messages across the devices
        self.basic_write('SND ' + message)

    def empty_buffer(self):  # clears the buffer of any old messages/data which will definitely occur
        self.input_ser.flush()

    def manual_commands(self):  # this method sucks, fix or delete
        while True:
            input_var = input("Command: ")  # waits for user input
            if input_var == "END":  # allows you to gracefully exit the method
                return
            else:
                self.basic_write(input_var)
                print(self.read_buffer())
                print(self.read_buffer())

    def read_buffer(self):  # just reading, no analysis of input whatsoever
        temp = self.input_ser.readline()
        return temp.decode()

    def read_received(self):  # reads any incoming messages ADJUST TO DEAL WITH SPLIT LINES!!!
        s = self.read_buffer()
        s = s.splitlines(True)
        data = []
        for line in s:  # reads all lines in the buffer
            if line is '\r':
                pass
            elif not line.endswith('\n'):
                # print("debug")
                self.line_frag += line
            else:
                line = self.line_frag + line
                error_split = line.splitlines(True)
                if len(error_split) > 1:
                    print(error_split)
                    s.extend(error_split[1:])
                    line = error_split[0]
                line = line.strip()
                if line.startswith('RCV'):
                    data.append(line[4:])  # sometimes
                elif line is not "":  # this is mostly a debugging line to tell any error messages
                    print(line)
                self.line_frag = ""
        '''if not data == []:
            print(data)'''
        return data

    def dummy_read(self, output_file, timey):
        while time.time() - timey < 10:
            bytesToRead = self.input_ser.inWaiting()
            temp = self.input_ser.read(bytesToRead)
            output_file.write(temp.decode())


class Position:
    def __init__(self, name, data, error):
        self.name = name
        self.data = data
        self.errors = error
        self.indexes = list(error.keys())
        for i in range(len(self.indexes)):
            self.indexes[i] = int(self.indexes[i])

    def __str__(self):
        return self.name.strip()

    def find_errors(self, current_data):  # maybe add check for both sensors vs. just one
        current_err = set()
        for i in range(6):
            if i in self.indexes:
                temp_err = self.errors[i]
                err = current_data[i] - self.data[i]
                if err < temp_err[0][0]:
                    current_err.add(temp_err[0][1])
                elif err > temp_err[1][0]:
                    current_err.add(temp_err[1][1])
        while 'NO_LABEL' in current_err:
            current_err.remove('NO_LABEL')  #makes things not be annoying
        return current_err

    def to_file(self, file):  # make sure file is open (and remember to close it elsewhere)
        file.write(self.name + '\n')
        for i in range(5):
            file.write(str(self.data[i]) + ' ')
        file.write(str(self.data[5]) + '\n')
        for i in self.indexes:
            file.write(str(i) + '\n')
            temp = self.errors[str(i)]
            for j in temp:
                file.write(str(j[0]) + ' ')
                file.write(j[1] + '\n')
        file.write('END\n')

    def label_error(self, err, is_negative, label):  # would be neat to have a dynamic version of this
        if is_negative:
            self.errors[err][0][1] = label
        else:
            self.errors[err][1][1] = label


class SmartProfile:  # basic user interface class
    def __init__(self, user, blue):
        self.user_name = user  # to be used in storing the data in a file, eventually
        self.read_rate = 0.2
        self.ble = blue
        self.output_file = open('data.txt', 'w')
        self.data_store = []
        self.positions = []
        self.read_position_file()

    def read_position_file(self, file='position_data.txt'):
        input_file = open(file)
        while True:
            line_in = input_file.readline()
            if 'DONE' in line_in:
                break
            else:
                title = line_in
                line_in = input_file.readline()
                data = line_in.split()
                for i in range(6):
                    data[i] = float(data[i])
                errs = dict()
                while True:
                    line_in = input_file.readline()
                    if 'END' in line_in:
                        break
                    else:
                        label = int(line_in)
                        for i in range(2):
                            line_in = input_file.readline()
                            temp_err = line_in.split()
                            if i is 0:
                                errs[label] = [(float(temp_err[0]), temp_err[1])]
                            else:
                                errs[label].append((float(temp_err[0]),temp_err[1]))
                self.positions.append(Position(title, data, errs))
        input_file.close()

    def cali_pos(self):  # maybe add a check if a position is too similar to an existing one?
        title = input("What is the name of this position (all caps)?")
        user_in = input('When in position, type \'BEGIN\'')
        while not user_in == 'BEGIN':
            if user_in == 'END':
                print('Calibration Cancelled by User')
                return
            user_in = input('Invalid input \n\r To end process type \'END\'')
        data = self.cali_helper()
        end_data = [0] * 6
        errs = dict()
        for i in range(6):
            temp_data = data[i]
            end_data[i] = temp_data[0]
            if abs(temp_data[1]) > 0.1:  # baseline of significance
                pass
            else:
                temp = []
                name = input('If you want to label a negative error in direction ' + str(
                    i) + ' type that label\nOtherwise, type \'NO\'')
                if name == 'NO':
                    temp.append([-temp_data[1], 'NO_LABEL'])
                    temp.append([temp_data[1], 'NO_LABEL'])
                else:
                    temp.append([-temp_data[1], name])
                    name = input('You must label a positive error in direction ' + str(
                        i))
                    temp.append([temp_data[1], name])
                errs[str(i)] = temp
        self.positions.append(Position(title, end_data, errs))

    def data_empty(self):
        return len(self.data_store) == 0

    def find_position(self, data):  # finds the position that the current data is most similar to
        similarities = [0] * len(self.positions)
        k = 0
        for i in range(6):
            k = 0
            for j in self.positions:
                if i in j.indexes:
                    similarities[k] += abs(data[i] - j.data[i])
                k += 1
        for j in range(len(self.positions)):
            similarities[j] /= len(self.positions[j].indexes)
        #print(similarities)
        current = min(similarities)
        return self.positions[similarities.index(current)]

    def cali_helper(self):
        self.reset_FIFO()
        stats_tgyr = [[0, 0], [0, 0], [0, 0]]  # storage container for mean and standard deviation of each variable
        stats_agyr = [[0, 0], [0, 0], [0, 0]]
        n = 0  # keeps track of number of entries
        s = [0] * 6  # storage for standard deviation
        while n < 30:  # arbitrary number of measurements to produce a reasonable average
            temp_mean_a = [stats_agyr[0][0], stats_agyr[1][0], stats_agyr[2][0]]  # stores the previous mean
            temp_mean_t = [stats_tgyr[0][0], stats_tgyr[1][0], stats_tgyr[2][0]]
            n += 1
            raw = self.read_data_FIFO()  # input new data
            print(raw)
            tgyr = raw[3:]
            agyr = raw[:3]
            for i in range(3):
                tgyr[i] = float(tgyr[i])
                agyr[i] = float(agyr[i])
            for i in range(3):  # calculates a running mean and standard deviation
                stats_tgyr[i][0] += (tgyr[i] - temp_mean_t[i]) / n
                stats_agyr[i][0] += (agyr[i] - temp_mean_a[i]) / n
                s[i] += (tgyr[i] - temp_mean_t[i]) * (tgyr[i] - stats_tgyr[i][0])
                s[i + 3] += (agyr[i] - temp_mean_a[i]) * (agyr[i] - stats_agyr[i][0])
        for i in range(3):  # end of the standard dev. calculation
            stats_tgyr[i][1] = math.sqrt(s[i] / (n - 2))
            stats_agyr[i][1] = math.sqrt(s[i + 3] / (n - 2))
        stats_tgyr.extend(stats_agyr)  # write this better
        print('You can move now, I\'m going to think for a while')
        return stats_tgyr

    def read_data_timed(self, t):  # edit to account for buffer sending multiple data
        start = time.time()
        self.data_empty()
        data = self.read_data_FIFO()
        counts = [0, 0]
        while time.time() - start < t:
            data.extend(self.read_data_FIFO())
            counts[0] += 1
        print("BACKLOG")
        '''while not self.data_empty(): # commented until I add a method to only collect old data
            data.append(self.read_data_FIFO())
            counts[1] += 1'''
        print(counts)
        # print(data)
        # self.write_to_file(data)  # might have to fix this method
        return data

    def write_to_file(self, data):
        st = ""
        n = 0
        for i in data:
            st += str(i)
            st += " "
            if n == 5:
                st += "\n"
                n = 0
            else:
                n += 1
        st += "\n"
        self.output_file.write(st)
        # print("done writing")

    def read_data_FIFO(self):
        value_ank = []
        value_toe = []
        a = False
        t = False
        while not (a and t and len(self.data_store) >= 4):  # causes issues if one mpu stops working (probably no fix)
            self.data_store.extend(self.ble.read_received())
            a = 'a' in self.data_store
            t = 't' in self.data_store
            if len(self.data_store) > 6:  # one of the mpus has stopped working
                print("mpu connection failure")
                self.data_store = []
                a = False
                t = False
            elif len(self.data_store) > 1:
                if not (self.data_store[0] == 'a' or self.data_store[0] == 't'):
                    self.data_store = self.data_store[1:]
                    print('offset')
        andex = self.data_store.index("a")
        tndex = self.data_store.index("t")

        ind = min(andex, tndex)
        if ind == andex:
            t = False
        else:
            a = False
        ind += 1
        for k in range(2):
            st = ''
            if self.data_store[ind].startswith('RCV'):  # should be unnecessary, annoyingly isn't
                self.data_store[ind] = self.data_store[ind][4:]
            if '.' in self.data_store[ind]:
                st += self.data_store[ind].strip()  # fix problem with floats
            ind += 2
            if a:
                value_ank = st.split()
            else:
                value_toe = st.split()
            a = not a
            t = not t
        if len(self.data_store) > 4:
            self.data_store = self.data_store[5:]
            print("overflow")
        else:
            self.data_store = []
        return value_ank + value_toe

    def reset_FIFO(self):
        start = time.time()
        while time.time() - start < 0.25:  # clears out anything left in the Serial buffer
            self.ble.read_received()
        self.data_store = []
        self.ble.empty_buffer()

    def error_check(self, data, position):  # future method to find the error state in the position
        return

    def read_continuous(self):
        data_store = []
        self.reset_FIFO()
        data = [0] * 6
        while no_input:
            temp = self.read_data_FIFO()
            for j in range(6):
                data[j] = float(temp[j])
            data_store.extend(data)
            pos = self.find_position(data)
            #print(data)
            print(pos)
            errs = pos.find_errors(data)
            st = ''
            for i in errs:
                st+=str(i)+', '
            if st is not '':
                print(st)
        return data_store


def check_input():  # thread to stop things with user input in the middle of the program
    global no_input
    no_input = True
    i = ' '
    while not i == '':
        i = input("hit enter to stop things \n")
        if not i == '':
            pass
            # print("writing to ble")
            # ble.basic_write(i)
    print("done")
    no_input = False


interrupt_check = threading.Thread(target=check_input)  # makes the thread work
interrupt_check.setDaemon(True)
ble = BLEInterface()  # instantiates the ble object
smart = SmartProfile("emma", ble)
'''for i in range(3):
    smart.cali_pos()
out_file = open('position_data.txt', 'w')
for j in smart.positions:
    j.to_file(out_file)
out_file.write('DONE')
out_file.close()'''
interrupt_check.start()
data = smart.read_continuous()
print("DONE")
smart.write_to_file(data)
smart.output_file.close()
import DataPlotter
