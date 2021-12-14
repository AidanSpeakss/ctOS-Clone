import socket, os, threading, gpiozero, bluetooth, uuid, subprocess, serial
# Custom Libs
import utils, config

global clients_bt
global clients_sock
clients_bt = []
clients_sock = []

def execShell(cmd_line):
    subprocess.call(cmd_line, shell=True)

def execScript(script):
    exec("from scripts import " + script)
    exec(script + ".main()")

def backgroundAPIThread(client):
    while True:
        request = client.recv(1024).decode()

        if request == "broadcast_to_all":
            client.send("ok".encode())
            message = client.recv(1024)
            for client_bt in clients_bt:
                client_bt.send(message)
            for client_sock in clients_sock:
                client_sock.send(message)
            client.send("done".encode())

        if request == "broadcast_to_bt":
            client.send("ok".encode())
            message = client.recv(1024)
            for client_bt in clients_bt:
                client_bt.send(message)
            client.send("done".encode())

        if request == "broadcast_to_sock":
            client.send("ok".encode())
            message = client.recv(1024)
            for client_bt in clients_bt:
                client_bt.send(message)
            client.send("done".encode())
        
        if request == "execscript":
            client.send("ok".encode())
            script = client.recv(1024).decode()
            thread = threading.Thread(target=execScript, args=[script])
            thread.start()
            client.send("done".encode())

def backgroundAPI():
    socke = socket.socket()
    socke.bind(("127.0.0.1", 8787))
    socke.listen()

    while True:
        client, client_info = socke.accept()
        thread = threading.Thread(target=backgroundAPIThread, args=[client])
        thread.start()

def ServThread(client, client_info):

    host,port = client.getpeername()

    while True:

        data = client.recv(1024).decode()
        print(data)
        if not data:
            break

        for custom_event in config.custom_events:
            if data.startswith(config.custom_events[custom_event] + " "):
                if config.custom_events[custom_event].startswith("execscript "):
                    thread = threading.Thread(target=execScript, args=[config.custom_events[custom_event]])
                    client.send("executed script " + custom_event)

                if config.custom_events[custom_event].startswith("shellexec "):
                    thread = threading.Thread(target=execShell, args=[config.custom_events[custom_event].replace("shellexec ", "")])
                    client.send("executed shell command " + custom_event)

        if data.startswith("serial_send "):
            ser = serial.Serial(port=data.split(" ")[1])
            ser.write(data.split(" ")[2])
            client.send("Sent".encode())

        if data.startswith("serial_recv "):
            ser = serial.Serial(port=data.split(" ")[1])
            client.send(ser.readall())

        if data == "serial_list":
            serials = ""
            serial_list = utils.serial_ports()
            for serial in serial_list:
                serials = serials + serial + "\n"
            client.send(serials.encode())

        if data.startswith("read_led "):
            pin = gpiozero.LED(data.split(" ")[1])
            if pin.is_active:
                client.send("1".encode())
            else:
                client.send("0".encode())
            pin.close
        
        if data.startswith("set_led "):
            pin = gpiozero.LED(data.split(" ")[1])

            if data.split()[2] == "1":
                pin.on()
            if data.split()[2] == "0":
                pin.off()

            client.send("Led set accordingly".encode())
            pin.close()

        if data.startswith("move_servo "):
            servo = gpiozero.AngularServo(data.split()[1], min_angle=-90, max_angle=90)
            servo.angle(int(data.split(" ")[2]))
            servo.close()

        if data.startswith("distancesensor_read "):
            pin = gpiozero.DistanceSensor(echo=data.split()[1],trigger=data.split()[2])
            client.send(str(pin.distance).encode())
            pin.close()

        if data.startswith("exec_script "):
            thread = threading.Thread(target=execScript, args=[data.split(" ")[1]])
            thread.start()
            client.send("Started script".encode())

        if data.startswith("transmitfm "):
            thread = threading.Thread(target=utils.transmitFM, args=[data.split(" ")[1], "sample_file.wav"])
            thread.start()
            client.send("Started transmitting".encode())

        if data.startswith("spi_write "):
            spi = gpiozero.SPI()
            spi.write(data.split(" ")[1])
            client.send("sent".encode())
            spi.close()
        
        if data.startswith("spi_read "):
            spi = gpiozero.SPI()
            client.send(str(spi.read(data.split(" ")[1])))
            spi.close()

def startServBLE():
    
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", 1))
    server_sock.listen(1)

    uuid1 = str(uuid.uuid4())

    bluetooth.advertise_service(server_sock, "CTOS v1", service_id=uuid1,
                            service_classes=[uuid1, bluetooth.SERIAL_PORT_CLASS],
                            profiles=[bluetooth.SERIAL_PORT_PROFILE],
                            # protocols=[bluetooth.OBEX_UUID]
                            )

    while True:
        client_sock, client_info = server_sock.accept()
        thread = threading.Thread(target=ServThread, args=[client_sock, client_info])
        thread.start()

def startServSOCK():

    sock = socket.socket()
    sock.bind(("0.0.0.0", 5753))
    sock.listen()

    client_sock, client_info = sock.accept()

    thread = threading.Thread(target=ServThread, args=[client_sock, client_info])
    thread.start()

def main():

    print("Starting CTOS v1...")
    socket_thread = threading.Thread(target=startServSOCK)
    background_thread = threading.Thread(target=backgroundAPI)
    bluetooth_thread = threading.Thread(target=startServBLE)

    socket_thread.start()
    print("Started socket server")

    background_thread.start()
    print("started background api")
    
    bluetooth_thread.start()
    print("Started bluetooth server")

    print("Starting startup scripts...")
    for script in os.listdir("scripts/"):
        with open("scripts/" + script, "r") as f:
            scriptCode = f.readline()
            if scriptCode == "#startup script":
                print("Starting script " + script)
                thread = threading.Thread(target=execScript, args=[script])
                thread.start()
                print("Started " + script)
    print("Finished starting scripts")

main()
