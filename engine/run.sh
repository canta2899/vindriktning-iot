cp /log/logfile.log /log/crashreport.log
cat /dev/null > /log/logfile.log
python3 /engine.py
