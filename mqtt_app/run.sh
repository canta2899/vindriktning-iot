# Obsolete script, not used anymore
cp /log/logfile.log /log/crashreport.log
cat /dev/null > /log/logfile.log
rm /log/logfile.log.offset
python3 /mqttapp.py
