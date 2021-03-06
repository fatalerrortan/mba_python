import csv
import traceback
import os
import logging
import asyncio

class Freq_Analyser:
    
    def __init__(self, currency:str):

        self.logger = logging.getLogger("root.{}".format(__name__))
        self.currency = currency
        self.freq_dict = {}
        self.freq_margin_list = []
        self.csv_file_path = 'data/{}.csv'.format(self.currency)
        self.__format_csv()
   
    def __format_csv(self):

        if not os.path.isdir("data"):
            os.makedirs("data", os.umask(0))

        if not os.path.isfile(self.csv_file_path):
            with open(self.csv_file_path, mode='w+') as csv_file:
                csv_file.write('{},{}\r\n'.format('margin', 'freq'))

        with open(self.csv_file_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                self.freq_dict[float(row['margin'])] = float(row['freq'])
                self.freq_margin_list.append(float(row['margin']))
                
    def set_freq(self, margin:float):
        if not margin in self.freq_margin_list:
            self.freq_margin_list.append(margin)
            self.freq_dict[margin] = 1 
        else:
            self.freq_dict[margin] += 1 

    def write_to_csv_at_exit(self, a, b):
        msg = '---> converting collected data to csv, then the program will be terminated ... <---'
        self.logger.info(msg)

        sorted_freq_dict = dict(sorted(self.freq_dict.items()))

        with open(self.csv_file_path, 'w') as csv_file:
            csv_file.write('{},{}\r\n'.format('margin', 'freq'))
            for margin, freq in sorted_freq_dict.items():
                csv_file.write('{},{}\r\n'.format(margin, freq))

        exit(self.logger.info('bye bye 再见 ciao wiedersehen :)'))

    async def write_to_csv_periodically(self):
        while True:
            await asyncio.sleep(60)
            msg = '---> writing analysis records <---'
            self.logger.info(msg)

            sorted_freq_dict = dict(sorted(self.freq_dict.items()))

            with open(self.csv_file_path, 'w') as csv_file:
                csv_file.write('{},{}\r\n'.format('margin', 'freq'))
                for margin, freq in sorted_freq_dict.items():
                    csv_file.write('{},{}\r\n'.format(margin, freq))

        
    def get_freq_result(self):
        pass


    
         