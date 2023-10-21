import sys
import re
import socket
import random
from concurrent.futures import ThreadPoolExecutor


FORMAT = 'utf-8'
MAX_MSG_LEN = 65000 # 1 character is 1 byte.
MAX_WORKERS =10
server = None
serverDisconnectMessage = "!EXIT"
clientDisconnectMessage = "!DISCONNECT"

# Number of current active threads
numberOfWorkers = 0


# Stores GAME IDs that were not finished
unresolvedSessions = []

# Winning positions in tic-tac-toe
winPos = [
    [0,2,4],
    [6,8,10],
    [12,14,16],
    [0,6,12],
    [2,8,14],
    [4,10,16],
    [0,8,16],
    [4,8,12]
]


def checkWinner(GAME_STATE):
    global winPos
    
    for positions in winPos:
        if (GAME_STATE >> positions[0]) & 3 == (GAME_STATE >> positions[1]) & 3 and (GAME_STATE >> positions[1]) & 3== (GAME_STATE >> positions[2]) & 3 and (GAME_STATE >> (positions[0])) & 3 == (GAME_STATE >> positions[2]) & 3 and (GAME_STATE >> positions[1]) & 3 != 0:
            return True
    return False

def checkTie(GAME_STATE):
    # Expects an int type function paramter
    
    # Check if the game is a tie
    freepos = 0
    for _ in range(9):
        if GAME_STATE & 3 == 0:
            freepos = freepos + 1
        GAME_STATE = GAME_STATE >> 2
    if freepos == 0:
        return True
    return False

def moveBot(GAME_STATE, botPiece):
    # Expects an integer input and another integer which indicates if it is an X or O
    # Check for free positions
    freePos =[]
    pos = 0
    tempData= GAME_STATE
    
    # Locate free positions
    for _ in range(9):
        if GAME_STATE & 3 == 0:
            freePos.append(pos)
        pos = pos + 2
        GAME_STATE = GAME_STATE >> 2
    
    # Choose randomly from a list of free positions 
    botChoice = freePos[random.randint(0,len(freePos) - 1)]
    # Update new data
    tempData = tempData + (botPiece << botChoice)

    return tempData
    
# Bit Operations
def binaryToInteger(binaryData):
    # Converts a string of binary data to it's integer equivalent 
    data = 0
    exp = 0
   
    # Leftmost bit is the least significant bit
    for i in range(len(binaryData)):
        data = data + (int(binaryData[i]) << exp)
        exp = exp + 1
    return data

def setBit(binaryData,bitNum):
    # Expects binaryData as integer as input and and integer called bitnum

    shiftOp = binaryData & (1 << bitNum)
    
    if shiftOp == 0:
        binaryData = binaryData + (1 << bitNum)
    return binaryData # return an integer base 10 representation of the binaryData

def clearBit(binaryData,bitNum):
   
    binaryData = binaryData - (binaryData & (1 << bitNum))
    return binaryData # return an integer base 10 representation of the binaryData
   
def integerToBinary(num,bit_len):
    # Return a string representation of the binary data
    binaryData = str(bin(num)).split('b')[1]

    diff = int(abs(bit_len - len(binaryData)))

    while diff != 0:
        binaryData = "0" + binaryData
        diff = diff - 1
    
    # Reverse results
    return binaryData[::-1]

def checkBit(binaryData, bitnum):
    # Expects an integer for binaryData and bitNum
    
    return binaryData & (1 << bitnum)


# ServerFunctions

def validAddress():
    # Validates the IP and Port number at the command line and returns the IP and Port as a tuple if both addres are valid. 
    ipInfo = sys.argv
    
    if len(ipInfo) < 3:
        print('Both IP address and port number are needed in the command line.')
        exit(1)
    else:
        IP = sys.argv[1]
        PORT = sys.argv[2]

        # A regex to validate an IPv4 Address
        isIPValid = re.search(r'^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])'
                              ,IP)
        if isIPValid == None:
            print(f'IP ADDRESS: {IP} IS INVALID')
            exit(1)
        
        # Check if PORT Number is valid
        try:
            PORT = int(PORT)
        except:
            print(f'Port : {PORT} is invalid.') 
            exit(1)
        return (IP,PORT)

def send(msg,client_socket):
    
    # Encode the string in utf-8 format
    message = msg.encode(FORMAT)
    msg_len = len(message)
    
    
    send_length = str(msg_len).encode(FORMAT)
    send_length += b' ' *(MAX_MSG_LEN - len(send_length))
    
    client_socket.send(send_length)
    client_socket.send(message)
    
def receive(client_socket):

    # Receive message from client
    
    msg_len = client_socket.recv(MAX_MSG_LEN).decode(FORMAT)
    
    if msg_len:
        msg_len = int(msg_len)

        # Get the actual message sent by the client
        message = client_socket.recv(msg_len).decode(FORMAT)
                
        return message
    return msg_len
    
def handle_client(client_address,client_socket):
    GAME_ID = None
    connected = True 
    global server
    global unresolvedSessions
    global numberOfWorkers
    global MAX_WORKERS
    
    numberOfWorkers = numberOfWorkers + 1
    
    if len(unresolvedSessions) > 0:
        print(f'GAME FLAG: 0000010000000')
        print(f'INVALID GAME ID: Client cannot connect. GAME ID/s in progress')
        for id in unresolvedSessions:
            print(integerToBinary(id,14))
        print('[CLOSING SESSION TO FREE SPACE]')
        unresolvedSessions = []
        send('invalid',client_socket)
        numberOfWorkers = numberOfWorkers - 1
        client_socket.close()
        return
    else:
        send('valid',client_socket)
        print(f"Accepted connection from {client_address[0]}:{client_address[1]}")    
        print(f'[ACTIVE SESSIONS] : {numberOfWorkers}')

    
    while connected:

        # First message received by the server when the client connects
        player_name = receive(client_socket)
        if player_name:
            # Disconnect client from the server
            if player_name == serverDisconnectMessage or player_name == clientDisconnectMessage:
                connected = False
                
                unresolvedSessions.append(random.randint(0, 2**24 - 1))
                print(f'[TIMEOUT ERROR] GAME FLAG: {random.randint(0,1)}0000100000000')
                client_socket.close()
                return
            
            print(f'Player Name: {player_name}')
            
            # Receive the game session ID
            if GAME_ID == None:
                GAME_ID = binaryToInteger(receive(client_socket))
            else:
                binaryToInteger(receive(client_socket)) # FLUSH OUT CONTENTS
                GAME_ID= -1

            # Generate an unsigned message ID
            MESSAGE_ID = random.randint(0, 2**8-1)

            GAME_FLAG = 0
            GAME_STATE = 0
            print(f'INITAL MESSAGE ID: {integerToBinary(MESSAGE_ID,8)} TO SEND TO PLAYER {player_name}')
            
            # Send initial message ID
            send(integerToBinary(MESSAGE_ID,8),client_socket)

            turn = receive(client_socket)
            
            if GAME_ID == -1:
                GAME_FLAG = setBit(GAME_FLAG,5)
                send(integerToBinary(GAME_FLAG,14),client_socket)
                send(f'INVALID GAME ID: An existing match is ongoing. Refused connection for {player_name}',client_socket)
                numberOfWorkers = numberOfWorkers - 1
                client_socket.close()
                return
            else:
                send(integerToBinary(0,14),client_socket)
                send('',client_socket)
                
                
            if turn == "1":
                send(f'PLAYER {player_name} TURN',client_socket)

            # Game start in server
            while connected:
                bitNum = 0
                ID = binaryToInteger(receive(client_socket))                        
                GAME_STATE = binaryToInteger(receive(client_socket))
                GAME_FLAG = binaryToInteger(receive(client_socket))
                TEMP_MESSAGE_ID = binaryToInteger(receive(client_socket))
                
                print(f'DATA RECEIVED FROM PLAYER {player_name}')
                print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                print(f'MESSAGE ID: {integerToBinary(TEMP_MESSAGE_ID,8)}\n')
                
                if GAME_FLAG == 0:
                    print(f'UNEXPECTED INTERRUPT FROM: {player_name}. Closing Connection')
                    unresolvedSessions.append(GAME_ID)
                    connected == False
                    numberOfWorkers = numberOfWorkers - 1
                    client_socket.close()
                    return
                

                 # Examine player movement
                invalidState = checkBit(GAME_FLAG,5)


                if invalidState != 0:

                    send(integerToBinary(GAME_STATE,18),client_socket)
                    send(integerToBinary(GAME_FLAG,14),client_socket)
                    send(integerToBinary(MESSAGE_ID,8),client_socket)
                    print(f'INVALID GAME STATE: Closing server. Error caused by {player_name}')
                    send(f'INVALID GAME STATE: Player {player_name} made an invalid move',client_socket)
                    numberOfWorkers = numberOfWorkers - 1
                    print(f'[ACTIVE CONNECTIONS]: {numberOfWorkers}')
                    client_socket.close()
                    return

                # Examine if the the difference between the previous message id and the current
                elif (int(abs(TEMP_MESSAGE_ID - MESSAGE_ID)) != 2**8 -1 and int(abs(TEMP_MESSAGE_ID - MESSAGE_ID)) != 1) :
                    GAME_FLAG = setBit(GAME_FLAG,5)
                    send(integerToBinary(GAME_STATE,18),client_socket)
                    send(integerToBinary(GAME_FLAG,14),client_socket)
                    send(integerToBinary(MESSAGE_ID + 1,8),client_socket)   

                    send(f'INVALID MESSAGE ID: Order of messages are not mantained for player {player_name}',client_socket)
                    print(f'INVALID MESSAGE ID: Closing server. Error caused by player {player_name}')
                    numberOfWorkers = numberOfWorkers - 1
                    print(f'[ACTIVE CONNECTIONS]: {numberOfWorkers}')

                    client_socket.close()
                    return
                
                MESSAGE_ID = TEMP_MESSAGE_ID
                MESSAGE_ID = MESSAGE_ID + 1
                
                if(MESSAGE_ID > 255):
                    MESSAGE_ID = 0
                
                print(f'DATA TO SEND TO PLAYER {player_name}')
                if checkBit(GAME_FLAG,0) == 0:
                    botMove = 2 # Bot has a move of 'O'
                else:
                    botMove = 1 # Bot has a move of 'X'
                
                # Check last move player made
                if checkWinner(GAME_STATE): 
                    if botMove == 1:
                        bitNum = 3
                    else:
                        bitNum = 2
                    GAME_FLAG = setBit(GAME_FLAG,bitNum)

                    print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                    print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                    print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                    print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                    
                    send(integerToBinary(GAME_STATE,18),client_socket)
                    send(integerToBinary(GAME_FLAG,14),client_socket)
                    send(integerToBinary(MESSAGE_ID,8),client_socket) 
                    send(f"PLAYER {player_name} WINS",client_socket)
                    break
                    
                elif checkTie(GAME_STATE):
                    print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                    print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                    print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                    print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                    
                    GAME_FLAG = setBit(GAME_FLAG,4)
                    send(integerToBinary(GAME_STATE,18),client_socket)
                    send(integerToBinary(GAME_FLAG,14),client_socket)
                    send(integerToBinary(MESSAGE_ID,8),client_socket)

                    send("IT'S A DRAW",client_socket) 

                    break
                
                else:    
                    
                    # Move AI bot
                    GAME_STATE = moveBot(GAME_STATE, botMove)

                    # Change turn 
                    if botMove == 1:
                        GAME_FLAG = setBit(GAME_FLAG,1)
                        GAME_FLAG = clearBit(GAME_FLAG,0)
                    else:
                        GAME_FLAG = setBit(GAME_FLAG,0)
                        GAME_FLAG = clearBit(GAME_FLAG,1)
                    # Check if AI wins
                    if checkWinner(GAME_STATE):
                        if botMove == 1:
                            bitNum = 2
                        else:
                            bitNum = 3
                        print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                        print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                        print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                        print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                        

                        GAME_FLAG = setBit(GAME_FLAG,bitNum)
                        send(integerToBinary(GAME_STATE,18),client_socket)
                        send(integerToBinary(GAME_FLAG,14),client_socket)
                        send(integerToBinary(MESSAGE_ID,8),client_socket) 
                        send(f"PLAYER COMPUTER WINS, PLAYER {player_name} LOSES",client_socket)
                        break
                    # Check if is a tie
                    elif checkTie(GAME_STATE):

                        GAME_FLAG = setBit(GAME_FLAG,4)

                        print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                        print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                        print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                        print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')


                        send(integerToBinary(GAME_STATE,18),client_socket)
                        send(integerToBinary(GAME_FLAG,14),client_socket)
                        send(integerToBinary(MESSAGE_ID,8),client_socket)
                        send("IT'S A DRAW",client_socket)
                        break
                    else:

                        print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                        print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                        print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                        print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                        
                        send(integerToBinary(GAME_STATE,18),client_socket)
                        send(integerToBinary(GAME_FLAG,14),client_socket)
                        send(integerToBinary(MESSAGE_ID,8),client_socket)
                        send(f'PLAYER {player_name} TURN',client_socket)
            restartGame = receive(client_socket)
            if restartGame == 'N' and connected:
                # Close connection from client 
                GAME_ID = None
                connected = False
                print(f'CLOSING CONNECTION for {player_name}')
                numberOfWorkers = numberOfWorkers - 1
                print(f'[ACTIVE CONNECTIONS]: {numberOfWorkers}')

            else:
                GAME_ID = None
    client_socket.close()
        
def run_server(ADDR):
    global server
    global unresolvedSessions
    global numberOfWorkers
    global MAX_WORKERS

    # Create threadpoolexecutor object
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    # Create socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # bind the socket to a specific address and port and listen for incoming connections
    server.bind(ADDR)

    print(f'Server listening on {ADDR[0]}:{ADDR[1]}')
    
    while True:

        server.listen()
         
        # Accept connection from client 
        client_socket, client_address = server.accept()
                
        pool.submit(handle_client,client_address,client_socket)
        
    

def main():
    # Contains IP Address and Port Number
    ADDRESS = validAddress()
    run_server(ADDRESS)
    
    
if __name__ == "__main__":
    main()

