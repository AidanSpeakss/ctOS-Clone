
import cv2, socket

def connectToBackground():
    sock = socket.socket()
    global sok
    sok = sock.connect(("127.0.0.1", 8787))

first_frame = None
frames = 0
cam = cv2.VideoCapture(1)
global status
status = 0
video = cv2.VideoCapture(cv2.CAP_V4L2)

while True:
    check, frame = video.read()
    frames = frames + 1
    status = 0
    gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray,(21,21),0)

    if first_frame is None:
        first_frame=gray
        continue

    delta_frame=cv2.absdiff(first_frame,gray)
    thresh_frame=cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
    thresh_frame=cv2.dilate(thresh_frame, None, iterations=2)

    (cnts,_)=cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in cnts:
        if cv2.contourArea(contour) < 10000:
            sok.send("broadcast_to_sock".encode())
            out = sok.recv(1024).decode()
            print(out)
            sok.send("Movement!".encode())
            out = sok.recv(1024).decode()
            print(out)
            continue
        status=1
        
        (x, y, w, h)=cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 3)

    key = cv2.waitKey(1)
