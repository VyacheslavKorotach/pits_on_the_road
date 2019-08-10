import os
import time
import json
import serial
import datetime
#import calendar
import re
import Adafruit_DHT
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import os.path

# Use "logical" pin numbers
GPIO.setmode(GPIO.BCM)

# Disable "This channel is already in use" warnings
GPIO.setwarnings(False)

# Setup LED's: 2 - green, 3 - yellow, 4 - red
# for i in range(2,5):

current_led = 22
GPIO.setup(current_led, GPIO.OUT)
GPIO.output(current_led, False)
print('gpio22 = false')
time.sleep(3)
GPIO.output(current_led, True)
print('gpoo22 = TRUE')

mqtt_user = os.environ["SMUGGLER_MQTT_USER"]
mqtt_host = os.environ["SMUGGLER_MQTT_HOST"]
mqtt_port = os.environ["SMUGGLER_MQTT_PORT"]
#smuggler_topic = os.environ["SMUGGLER_TOPIC"]
pits_topic = "owntracks/pits_detection/pits_detector_01"
mqtt_password = os.environ["SMUGGLER_MQTT_PASSWORD"]
#mqtt_client_id = os.environ["SMUGGLER_MQTT_CLIENT_ID"]
mqtt_client_id = "PD"
#mqtt_posting_delay = int(os.environ["SMUGGLER_MQTT_POSTING_DELAY"])
mqtt_posting_delay = 1
ftp_host = os.environ["SMUGGLER_FTP_HOST"]
ftp_user = os.environ["SMUGGLER_FTP_USER"]
ftp_password = os.environ["SMUGGLER_FTP_PASSWORD"]
photo_path = '/home/pi/projects/smuggler_photos/'
max_ftp_error = 8
max_gps_error = 8
max_mqtt_error = 8
mqtt_retain = 1
at_sim_delay = 0.5
photo_width = 640
photo_height = 480
ser = serial.Serial('/dev/ttyS0')
ser.baudrate = 115200
ser.isOpen()
sensor_args = {'11': Adafruit_DHT.DHT11,
               '22': Adafruit_DHT.DHT22,
               '2302': Adafruit_DHT.AM2302}
sensor = sensor_args['11']
sensor_pin = 16


def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))


def on_message(mqttc, obj, msg):
    print('-----------')
    print('here is message on mqtt')
    print('-----------')
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
#    sensor_str = str(msg.payload)


def on_publish(mqttc, obj, mid):
    print("mid: " + str(mid))
    pass


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc, obj, level, string):
    print(string)


def at_sim7000(at_command):  # send 'AT..' command to the sim7000C modem
    ser.write(bytes(at_command + "\r\n", encoding='utf-8'))
    time.sleep(at_sim_delay)
    out = ''
    while ser.inWaiting() > 0:
        out += "".join(map(chr, ser.read(1)))  # ser.read(1).decode()
    if out != '':
        print(">>" + out)
    return out


def sim7000_mqtt_init():
    print('<-- sim7000_mqtt_init')
    sim7000_mqtt_init = ['AT+CNACT=2,"www.kyivstar.net"',
                         'AT+SMCONF="CLIENTID",' + mqtt_client_id,
                         'AT+SMCONF="KEEPTIME",60', 'AT+SMCONF="CLEANSS",1',
                         'AT+SMCONF="URL","' + mqtt_host + ':' + mqtt_port + '"',
                         'AT+SMCONF="USERNAME","' + mqtt_user + '"',
                         'AT+SMCONF="PASSWORD","' + mqtt_password + '"',
                         'AT+SMCONF="RETAIN",' + str(mqtt_retain),
                         'AT+SMCONF?', 'AT+SMCONN']
    resp = 'ERROR'
    attempt = 0
    while resp.find('ERROR') != -1 and attempt <= max_mqtt_error:
        attempt += 1
        sim7000_gprs_init()
        for sim7000_command in sim7000_mqtt_init:
            resp = at_sim7000(sim7000_command)
            if sim7000_command.find('AT+CNACT') != -1:
                time.sleep(3)
        if resp.find('ERROR') != -1:
            at_sim7000('AT+SMDISC')
            time.sleep(3)
            at_sim7000('AT+CNACT=0')
            time.sleep(3)
        time.sleep(3)
    return resp


def sim7000_mqtt_publish(topic, message):  # send the 'message' to the 'topic' by the sim7000 mqtt
    print('<-- sim7000_mqtt_publish')
    resp = 'ERROR'
    while resp.find('OK') == -1 or resp.find('ERROR') != -1:
        sim7000_mqtt_init()
        resp = at_sim7000('AT+SMSUB="' + topic + '",1')
        time.sleep(1)
        resp = resp + at_sim7000('AT+SMPUB="' + topic + '",' + str(len(message)) + ',1,' + str(mqtt_retain))
        ser.write(bytes(message, encoding='utf-8'))
        time.sleep(1)
        out = ''
        while ser.inWaiting() > 0:
            out += "".join(map(chr, ser.read(1)))  # ser.read(1).decode()
        resp = resp + out
        if out != '':
            print(">>" + out)
    time.sleep(1)
    at_sim7000('AT+SMUNSUB="' + topic + '"')
    time.sleep(1)
    at_sim7000('AT+SMDISC')
    time.sleep(1)
    at_sim7000('AT+CNACT=0')
    time.sleep(1)
    return resp


def sim7000_ftp_file_upload(source_name, dest_name):
    print('<-- sim7000_ftp_file_upload')
    if not os.path.exists(source_name):
        print("file to upload ", source_name, " doesn't exist")
        time.sleep(8)
        return 0
    sim7000_ftp_init = ['AT+SAPBR=3,1,"APN","www.kyivstar.net"', 'AT+SAPBR=1,1', 'AT+SAPBR=2,1',
                        'AT+FTPCID=1', 'AT+FTPSERV="' + ftp_host + '"', 'AT+FTPUN="' + ftp_user + '"',
                        'AT+FTPPW="' + ftp_password + '"', 'AT+FTPPUTNAME="' + dest_name + '"',
                        'AT+FTPPUTPATH="/files/"', 'AT+FTPPUT=1']
    resp = '+FTPPUT: 1,61'
    while resp.find('+FTPPUT: 1,61') != -1:
        sim7000_gprs_init()
        for sim7000_command in sim7000_ftp_init:
            resp = at_sim7000(sim7000_command)
            if sim7000_command.find('AT+FTPPUT=') != -1:
                time.sleep(3)
        if resp.find('+FTPPUT: 1,61') != -1:
            at_sim7000('AT+CNMP=13')
            time.sleep(2)
    time.sleep(3)
    file_len = os.path.getsize(source_name)
    handle = open(source_name, 'rb')
    block_size = 100
    data = handle.read(block_size)
    error_count = 0
    total_error_count = 0
    total_wrote = 0
    while True:
        resp1 = at_sim7000('AT+FTPPUT=2,' + str(len(data)))
        if resp1.find('+FTPPUT: 2,') != -1:
            wrote = ser.write(data)
            out = ''
            while ser.inWaiting() > 0:
                out += "".join(map(chr, ser.read(1)))  # ser.read(1).decode()
            if out != '':
                resp2 = out
                print(">>" + out)
            else:
                resp2 = at_sim7000('')
            if wrote == len(data):
                if resp2.find('ERROR') == -1:
                    if resp2.find('+FTPPUT: 1,1,') != -1:
                        block_size_str = resp2.split(',')[2].split('\r')[0]
                        block_size = int(re.sub('[^0-9]+', '', block_size_str))
                    error_count = 0
                    total_wrote = total_wrote + wrote
                    data = handle.read(block_size)  # shift this line under if..
                else:
                    error_count += 1
                    total_error_count += 1
                    time.sleep(error_count)
            else:
                print('wrote = ', wrote, ' ; len(data) = ', len(data))
        else:
            error_count += 1
            total_error_count += 1
            time.sleep(error_count)
        if not data or error_count > max_ftp_error:
            handle.close()
            break
    at_sim7000('AT+FTPPUT=2,0')
    time.sleep(1)
    at_sim7000('AT+SAPBR=0,1')
    print('total_error_count = ', total_error_count)
    percent_wrote = int(total_wrote / file_len * 100)
    return percent_wrote


def sim7000_gprs_init():
    print('<-- sim7000_gprs_init')
    sim7000_gprs_init = ['AT', 'AT', 'AT+CNMP=51', 'AT+CMNB=3', 'AT+CFUN=0', 'AT+CFUN=1', 'AT+CSQ',
                         'AT+CPSI?', 'AT+COPS?', 'AT+CIPSHUT', 'AT+CIPCSGP=1,"www.kyivstar.net"',
                         'AT+CSTT', 'AT+CIICR', 'AT+CIFSR', 'AT+CGPADDR']
    resp = 'ERROR'
    while resp.find('ERROR') != -1:
        for sim7000_command in sim7000_gprs_init:
            resp = at_sim7000(sim7000_command)
            if sim7000_command.find('AT+CFUN') != -1:
                time.sleep(3)
            if sim7000_command.find('AT+CIICR') != -1:
                time.sleep(3)
    return resp


def gps_init():
    print('<-- gps_init')
    sim7000_gps_init = ['AT+CGNSPWR=0', 'AT+CGNSPWR=1', 'AT+CGNSINF']
    resp = ''
    for sim7000_command in sim7000_gps_init:
        resp = at_sim7000(sim7000_command)
        time.sleep(3)
    return resp


def get_gps():
    print('<-- get_gps')
    utc_time = ''
    latitude = ''
    longitude = ''
    gps_info = {}
    j = 0
    while utc_time == '' and j <= max_gps_error:
        resp = 'ERROR'
        j += 1
        for i in range(max_gps_error):
            resp = at_sim7000('AT+CGNSINF')
            time.sleep(3)
            if resp.find('ERROR') == -1:
                break
            time.sleep(i)
        if resp != '':
            utc_time = resp.split(',')[2]
            latitude = resp.split(',')[3]
            longitude = resp.split(',')[4]
        lat = 0.0
        lon = 0.0
        tst = 0
        if latitude != "" and longitude != "" and utc_time != "":
            lat = float(latitude)
            lon = float(longitude)
            tst = int(utc_time.split('.')[0])
            tst = int(time.time())
#            tst = calendar.timegm(time.gmtime())
        gps_info = dict(tid=mqtt_client_id, lat=lat,
                        lon=lon, _type="location", batt=98, acc=8, p=100, vac=10,
                        t="u", conn="w", tst=tst, alt=106)
#tst=int(round(time.time() * 1000)
    if utc_time == '':
        gps_init()
    return gps_info


def take_photo():
    print('<-- take_photo')
    now = str(datetime.datetime.now())
    now = now.replace(' ', '').replace('-', '').replace(':', '').replace('.', '')
    photo_name = now + '.jpg'  # if not camera comment this line
#    photo_name = '20190519122325647588.jpg'  # del this string and uncomment two others
    photo_full_name = photo_path + photo_name
    take_photo_cmd = 'raspistill -vf -hf -o ' + photo_full_name + ' -w ' + str(photo_width) + ' -h ' + str(photo_height)
    GPIO.output(current_led, False)
    time.sleep(0.5)
    out = os.popen(take_photo_cmd).read()  # if not camera comment this line
    GPIO.output(current_led, True)
    print(out)  # if not camera comment this line
    return (photo_name)

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError:
        return False
    return True


sim7000_gprs_init()
gps_init()
info_str = get_gps()

local_mqtt_user = "sensors_sender"
local_mqtt_host = "localhost"
local_mqtt_port = 1883
local_mqtt_topic = "sensors"
local_mqtt_password = "password_03"
mqttc = mqtt.Client()
mqttc.username_pw_set(local_mqtt_user, password=local_mqtt_password)
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
mqttc.connect(local_mqtt_host, 1883, 60)
local_auth = {'username': local_mqtt_user, 'password': local_mqtt_password}
mqttc.loop_start()
#mqttc.loop_forever()
time.sleep(1)

while True:
#    photo_name = take_photo()
    #    photo_name = ''  # change it with above line
#    info_str = get_gps()
    sensor_str = subscribe.simple(local_mqtt_topic, hostname=local_mqtt_host, auth=local_auth, retained=False, msg_count=1)
    info_str = get_gps()
    #    info_str['humidity_%'], info_str['temperature_C'] = Adafruit_DHT.read_retry(sensor, sensor_pin)
    #    print(sensor_str)
    json_string = ''
    d = ''
    try:
        json_string = sensor_str.payload.decode('ascii')
    except UnicodeDecodeError:
        print("it was not a ascii-encoded unicode string")
    if json_string != '' and is_json(json_string):
        d = json.loads(json_string)
        info_str.update(d)
    print('d=', d)
    time.sleep(1)
#    info_str['photo'] = 'http://korotach.com/smuggler_photos/01/' + photo_name
#    info_str['uploaded_%'] = sim7000_ftp_file_upload(photo_path + photo_name, photo_name)
    print('--------------------')
    print(info_str)
    print('--------------------')
#    sim7000_mqtt_publish(pits_topic, json.dumps(info_str))
    pub_str = json.dumps(info_str)
    sim7000_mqtt_publish(pits_topic, pub_str.replace(" ",""))
    for i in range(mqtt_posting_delay):
        print('sleeping for ', mqtt_posting_delay - i, ' sec')
        time.sleep(1)

# ser.close()
