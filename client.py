import sys
import re
import socket
import random
from concurrent.futures import ThreadPoolExecutor

FORMAT = 'utf-8'
MAX_MSG_LEN = 65000 # 1 character is 1 byte,
MAX_IDLE_TIME = 60 * 5 # Max idle time for a player in seconds

server = None
serverDisconnectMessage = "!EXIT"
clientDisconnectMessage = "!DISCONNECT"
client = None

def binaryToInteger(binaryData):
    # The function has an integer parameter as input
    data = 0
    exp = 0

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
    # Expects a integer called binaryData which contains status about games and and integer called bitnum
   
    binaryData = binaryData - (binaryData & (1 << bitNum))
    return binaryData # return an integer base 10 representation of the binaryData

def integerToBinary(num,bit_len):
    # Return a string representation of the binary data
    binaryData = str(bin(num)).split('b')[1]

    diff = int(abs(bit_len - len(binaryData)))
    
    while diff != 0:
        binaryData = "0" + binaryData
        diff = diff - 1    
    # Reverse data 
    return binaryData[::-1]

def checkBit(binaryData, bitnum):
    # Expects an integer for binaryData and bitNum
    
    return binaryData & (1 << bitnum)

#Display
def printBoard(pieces):
    row = 1
    piece_num = 0

    while row < 11:
        column = 0
        if row == 1:
            while column < 19:
                if column % 2 == 0:
                    print(' ', end ='')
                else:
                    print('_',end = '')
                column = column + 1
        else:
            if row % 3 == 0:
                while column < 19:
                    if column % 6 == 0:
                        print('|',end='')
                    elif column % 3 == 0 and column % 6 != 0:
                        print(pieces[piece_num],end='')
                        piece_num = piece_num + 1
                    else:
                        print(' ',end='')
                    column = column  + 1
            elif (row-1)%3 == 0:
                while column < 19:
                    if column % 6 == 0:
                        print('|',end ='')
                    elif column % 2 == 0:
                        print('_',end = '')
                    else:
                        print(' ',end = '')
                    column = column + 1
            else:
                while column < 19:
                    if column % 6 == 0:
                        print('|',end ='')
                    else:
                        print(' ',end = '')
                    column = column + 1
        print()
        row = row + 1

def getBoardPieces(gameState):
    # gameState- n-bit str input
    
    moveList = binaryToInteger(gameState)
    pieces = []

    for _ in range(9):
        fieldState = moveList & 3 # Always get the lowest two bits
        if fieldState == 0:
            pieces.append(' ')
        elif fieldState == 1:
            pieces.append('X')
        elif fieldState == 2:
            pieces.append('O')
        moveList = moveList >> 2
    
    # Returns a list of 'X', 'O', or ' ' string characters
    return pieces

# User Movement Functions
def examineGameState(gameState,pos):
# gameState - a string of of binary

    # check if binary data is entered by the user
    if len(gameState) == 18:
        # check if the string data are integers
        try:
            binaryToInteger(gameState)
        except:
            return False
        # Check if each characters are bit
        for bit in gameState:
            if bit != "0" and bit != "1":
                return False
        
        stateNum = binaryToInteger(gameState)
        
        # Check if there is a "11" present into a 2-bit subfield
        while stateNum > 0:
            if stateNum & 3 == 3:
                return False
            stateNum = stateNum >> 2
        
         
        stateNum = binaryToInteger(gameState)
        # check if the position entered by the user is occupied
        if ((stateNum >> 2*(pos - 1)) & 3) != 0:
            return False
        # Game state is valid
        return True
    else:
        return False

def validateUserInput(gameState):
    # Player should choose a value between 1-9 (Valid Moves)
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        choice = pool.submit(input,'Pick your move between[1-9]: ').result(timeout=MAX_IDLE_TIME)
    except:
        print("[TIME OUT ERROR] Maximum idle time exceeded")
        return clientDisconnectMessage
    if choice == clientDisconnectMessage:
        return clientDisconnectMessage
    
    try:
        choice = int(choice)
    except:
        return -1
    
    if choice > 9 or choice < 1:
        return -1

    isValid = examineGameState(integerToBinary(gameState,18),choice)
    
    if isValid == False:
        return -1
    return choice

# Client-side functions

def validAddress():
    # Validates the IP and Port number at the command line and returns the IP and Port as a tuple if both addres are valid. 
    ipInfo = sys.argv
    
    if len(ipInfo) < 3:
        print('Both IP address and port number are needed in the command line.')
        exit(1)
    else:
        IP = sys.argv[1]
        PORT = sys.argv[2]

        # using regex that will validate an IPv4 Address
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

def send(msg):
    # Send a message to the server

    # Encode the string in utf-8 format
    message = msg.encode(FORMAT)
    msg_len = len(message)
    
    
    send_length = str(msg_len).encode(FORMAT)
    send_length += b' ' *(MAX_MSG_LEN - len(send_length))
    
    global client
    client.send(send_length)
    client.send(message)
    
def receive():
    # Receive message from server
    global client
    msg_len = client.recv(MAX_MSG_LEN).decode(FORMAT)
    
    if msg_len:
        msg_len = int(msg_len)

        # Get the actual message sent by the server
        message = client.recv(msg_len).decode(FORMAT)
                
        return message
    return msg_len


def run_client(ADDRESS):
    global serverDisconnectMessage
    global client

    # Create a thread pool
    pool = ThreadPoolExecutor(max_workers=1)
    
    # Create socket object 
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Establish connection with the server
    client.connect(ADDRESS)
    connected = True
    player_move = 0
    restartGame = 'N'
    playerName = ""
    
    # Validate if it is not a GAME ID error
    isGameValid = receive()
    
    if isGameValid != 'valid':
        print('INVALID GAME ID')
        connected = False 
    while connected:
        if restartGame == 'N':
            try:
                playerName = pool.submit(input, 'Enter your name:').result(timeout=MAX_IDLE_TIME)
                send(playerName)
            except:
                print("\nTIME OUT ERROR: No response from the client")
                playerName = clientDisconnectMessage
                send(clientDisconnectMessage)
            if playerName == clientDisconnectMessage:
                sys.exit()
                
        else:
            send(playerName)
        # Turn 0 - Computer First, Turn 1 - Player First
        turn = 0
        # Generate randomized unsigned int between 0 to 2^24 - 1
        GAME_ID = random.randint(0,2**24-1)
        
        # Sends the gameID in progress

        send(integerToBinary(GAME_ID,24)) 
        
        GAME_FLAG = 0
        GAME_STATE = 0
        MESSAGE_ID =  binaryToInteger(receive())

        send(f'{turn}')
        
        GAME_FLAG = binaryToInteger(receive())
        SERVER_MESSAGE = receive()

        if GAME_FLAG != 0:
            print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
            print(SERVER_MESSAGE)
            client.close()
            sys.exit(1)
            
        if turn == 1:
            SERVER_MESSAGE = receive()
            print(SERVER_MESSAGE)
            printBoard([' ',' ',' ',' ',' ',' ',' ',' ',' '])
        else:
            # Mantains proper formatting of message 
            MESSAGE_ID = MESSAGE_ID - 2
            
        # Start the game and continuously examine if someone wins or it is a tie
        while connected and checkBit(GAME_FLAG,2) == 0 and checkBit(GAME_FLAG,3) == 0 and checkBit(GAME_FLAG,4) == 0:
            if turn == 0:
                if MESSAGE_ID == 2**8 - 1:
                    MESSAGE_ID = -1
                GAME_FLAG = setBit(GAME_FLAG,0)
                GAME_FLAG = clearBit(GAME_FLAG,1)
    
                send(integerToBinary(GAME_ID,24))
                send(integerToBinary(GAME_STATE,18))
                send(integerToBinary(GAME_FLAG,14))
                send(integerToBinary(MESSAGE_ID + 1, 8))

                GAME_STATE = binaryToInteger(receive())
                GAME_FLAG = binaryToInteger(receive())
                MESSAGE_ID =  binaryToInteger(receive())
                SERVER_MESSAGE = receive()


                if checkBit(GAME_FLAG,2) != 0 or checkBit(GAME_FLAG,3) != 0 or checkBit(GAME_FLAG,4) != 0:
                    
                    pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                    printBoard(pieces)
                    
                    print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                    print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                    print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                    print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                    print(SERVER_MESSAGE)
                    break
                # Close server on error
                elif player_move == -1 or "INVALID" in SERVER_MESSAGE:
                    print(f'GAME FLAGS: {integerToBinary(GAME_FLAG,14)}')
                    print(SERVER_MESSAGE)
                    sys.exit(1)

                pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                printBoard(pieces)

                GAME_FLAG = setBit(GAME_FLAG,1)
                GAME_FLAG = clearBit(GAME_FLAG,0)
                
                # Client's turn
                print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')

                print(SERVER_MESSAGE)
                player_move = validateUserInput(GAME_STATE)

                # Disconnect client from server
                if player_move == clientDisconnectMessage:
                    send(integerToBinary(GAME_ID,24))
                    send(integerToBinary(GAME_STATE,18))
                    send(integerToBinary(0,14))
                    send(integerToBinary(MESSAGE_ID + 1, 8))         
                    print("[DISCONNECTING CLIENT FROM SERVER]")
                    client.close()
                    sys.exit()
                # If the move is not legal modify the error bit in the game flag
                if player_move == -1:
                    GAME_FLAG = setBit(GAME_FLAG,5)
                else:
                    # set bit for the player move
                    GAME_STATE = GAME_STATE + (2 << 2 * (player_move - 1))

                pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                printBoard(pieces)

                # Rollover if message id reaches the max size
                if MESSAGE_ID + 1 == 2 ** 8: 
                    MESSAGE_ID = -1
                
            else:
                GAME_FLAG = setBit(GAME_FLAG,0)

                # Print game status
                print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                
                print(SERVER_MESSAGE)

                player_move = validateUserInput(GAME_STATE)

                # Disconnect client from server
                if player_move == clientDisconnectMessage:
                    send(integerToBinary(GAME_ID,24))
                    send(integerToBinary(GAME_STATE,18))
                    send(integerToBinary(0,14))
                    send(integerToBinary(MESSAGE_ID + 1, 8))         
                    print("[DISCONNECTING CLIENT FROM SERVER]")
                    client.close()
                    sys.exit()
                # If the move is not modify the error bit in the game flag
                if player_move == -1:
                    GAME_FLAG = setBit(GAME_FLAG,5)
                else:
                    # set bit for the player move
                    GAME_STATE = GAME_STATE + (1 << 2 * (player_move - 1))
                
                pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                printBoard(pieces)
                
                GAME_FLAG = setBit(GAME_FLAG,1)
                GAME_FLAG = clearBit(GAME_FLAG,0)

                # Rollover if message id reaches the max size
                if MESSAGE_ID + 1 == 2 ** 8: 
                    MESSAGE_ID = -1


                # Send game information to the client
                send(integerToBinary(GAME_ID,24))
                send(integerToBinary(GAME_STATE,18))
                send(integerToBinary(GAME_FLAG,14))
                send(integerToBinary(MESSAGE_ID + 1, 8))
          
                # Receive updated information from server
                GAME_STATE = binaryToInteger(receive())
                GAME_FLAG = binaryToInteger(receive())
                MESSAGE_ID =  binaryToInteger(receive())             
                SERVER_MESSAGE = receive()

                if checkBit(GAME_FLAG,2) != 0 or checkBit(GAME_FLAG,3) != 0 or checkBit(GAME_FLAG,4) != 0:
                    if(checkBit(GAME_FLAG,3) != 0):
                        pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                        printBoard(pieces)
            
                    print(f'GAME ID: {integerToBinary(GAME_ID,24)}')
                    print(f'GAME FLAG: {integerToBinary(GAME_FLAG,14)}')
                    print(f'GAME STATE: {integerToBinary(GAME_STATE,18)}')
                    print(f'MESSAGE ID: {integerToBinary(MESSAGE_ID,8)}\n')
                    print(SERVER_MESSAGE)
                    break
                # Close server on error
                elif player_move == -1 or "INVALID" in SERVER_MESSAGE:
                    print(f'GAME FLAGS: {integerToBinary(GAME_FLAG,14)}')
                    print(SERVER_MESSAGE)
                    sys.exit(1)
                else:
                    print(SERVER_MESSAGE)
                    
                # Player AI MOVE
                pieces = getBoardPieces(integerToBinary(GAME_STATE,18))
                printBoard(pieces)
        
        restartGame = input('RESTART GAME WITH SAME USERNAME?(Y/N):')
        
        try:
            while restartGame != 'Y' and restartGame != 'N':
                restartGame = pool.submit(input,'RESTART GAME WITH SAME USERNAME?(Y/N):').result(timeout=MAX_IDLE_TIME)
        except:
            print(f'TIME OUT ERROR GAME ID {GAME_ID}')
            restartGame = 'N'
            
        send(restartGame)
        
        if restartGame == 'N':
            connected = False
            print("[DISCONNECTING CLIENT FROM SERVER]")

    # Remove client from the server
    pool.shutdown()
    client.close()
      

def main():
    ADDRESS = validAddress()
    run_client(ADDRESS)

if __name__ == '__main__':
    main()

