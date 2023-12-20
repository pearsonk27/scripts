"""Search all files in a directory for a text string"""
import os

DIRECTORY = 'Y:\\BACKUP_ONLINE_DB'

for filename in os.listdir(DIRECTORY):
    f = os.path.join(DIRECTORY, filename)

    if os.path.isfile(f):
        with open(f, encoding='utf-8') as ff:
            for row in ff.readlines():
                if row.find('gaaccountant2yr') != -1:
                    print(filename)
                