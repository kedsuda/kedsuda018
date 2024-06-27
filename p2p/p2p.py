import socket #สำหรับการสร้างการเชื่อมต่อเครือข่าย.
import threading #สำหรับการใช้งานเธรด.
import json # สำหรับการแปลงข้อมูลระหว่าง JSON และ Python objects.
import sys #สำหรับการทำงานกับระบบ interpreter (เช่น การรับค่าจากบรรทัดคำสั่ง)
import os #นำเข้าโมดูล os สำหรับการทำงานกับระบบไฟล์และการทำงานเกี่ยวกับระบบปฏิบัติการ.
import secrets # นำเข้าโมดูล secrets สำหรับการสร้างตัวเลขสุ่มที่ปลอดภัย.


""" การรันโปรแกรมบนสองเครื่อง:
บนเครื่องแรก: python p2p_node.py 5000
บนเครื่องที่สอง: python p2p_node.py 5001
ใช้ตัวเลือกที่ 1 บนเครื่องใดเครื่องหนึ่งเพื่อเชื่อมต่อกับอีกเครื่อง """

class Node:
    def __init__(self, host, port):
        self.host = host #กำหนดค่า host ที่โหนดนี้จะใช้
        self.port = port #กำหนดค่า port ที่โหนดนี้จะใช้.
        self.peers = []  # เก็บรายการ socket ของ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #สร้าง socket ใหม่ด้วย IPv4 และ TCP.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #ตั้งค่า socket เพื่อให้สามารถใช้งานซ้ำได้
        self.transactions = []  # สร้างลิสต์เปล่าสำหรับเก็บรายการ transactions
        self.transaction_file = f"transactions_{port}.json"  # กำหนดชื่อไฟล์สำหรับบันทึก transactions
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address สำหรับโหนดนี้

    def generate_wallet_address(self): #ฟังก์ชันสำหรับสร้าง wallet address ใหม่.
        # สร้าง wallet address แบบง่ายๆ (ในระบบจริงจะซับซ้อนกว่านี้มาก)
        return '0x' + secrets.token_hex(20) #สร้าง string ที่เริ่มต้นด้วย '0x' ตามด้วยตัวเลขสุ่ม 20 ไบต์ในรูปแบบของ hexadecimal.

    def start(self): #ฟังก์ชันสำหรับเริ่มต้นการทำงานของโหนด.
        # เริ่มต้นการทำงานของโหนด
        self.socket.bind((self.host, self.port)) # ผูก socket กับ host และ port ที่กำหนด.
        self.socket.listen(1) # ตั้งค่า socket ให้รอรับการเชื่อมต่อ.
        print(f"Node listening on {self.host}:{self.port}") #แสดงข้อความว่าโหนดกำลังรอรับการเชื่อมต่อ.
        print(f"Your wallet address is: {self.wallet_address}") #แสดง wallet address ของโหนด.

        self.load_transactions()  # โหลด transactions จากไฟล์ (ถ้ามี)

        # เริ่ม thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections) #สร้าง thread ใหม่สำหรับรับการเชื่อมต่อ.
        accept_thread.start() #เริ่ม thread สำหรับรับการเชื่อมต่อ.

    def accept_connections(self): # ฟังก์ชันสำหรับรอรับการเชื่อมต่อใหม่.
        while True: # ทำงานวนซ้ำตลอดเวลา
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()  #รับการเชื่อมต่อใหม่และเก็บข้อมูลของ client.
            print(f"New connection from {address}") #แสดงข้อความเมื่อมีการเชื่อมต่อให

            # เริ่ม thread ใหม่สำหรับจัดการการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,)) # สร้าง thread ใหม่สำหรับจัดการกับการเชื่อมต่อนี้
            client_thread.start() # เริ่ม thread สำหรับจัดการการเชื่อมต่อ

    def handle_client(self, client_socket): # ฟังก์ชันสำหรับจัดการการเชื่อมต่อกับ client
        while True: #ทำงานวนซ้ำตลอดเวลา
            try: #เริ่มบล็อกการตรวจจับข้อผิดพลาด
                # รับข้อมูลจาก client
                data = client_socket.recv(1024) #รับข้อมูลจาก client (สูงสุด 1024 ไบต์)
                if not data: #ตรวจสอบว่ามีข้อมูลหรือไม่
                    break # ถ้าไม่มีข้อมูลให้หยุดการวนซ้ำ
                message = json.loads(data.decode('utf-8'))  #แปลงข้อมูลที่ได้รับจาก JSON เป็น Python object
                
                self.process_message(message) #ประมวลผลข้อความที่ได้รับ

            except Exception as e: #จับข้อผิดพลาดถ้ามี
                print(f"Error handling client: {e}") # แสดงข้อความข้อผิดพลาด
                break #หยุดการวนซ้ำถ้ามีข้อผิดพลาด

        client_socket.close() # ปิดการเชื่อมต่อกับ client.

    def connect_to_peer(self, peer_host, peer_port): # ฟังก์ชันสำหรับเชื่อมต่อกับ peer อื่น.
        try: #เริ่มบล็อกการตรวจจับข้อผิดพลาด.
            # สร้างการเชื่อมต่อไปยัง peer
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # สร้าง socket ใหม่สำหรับการเชื่อมต่อกับ peer.
            peer_socket.connect((peer_host, peer_port)) #  เชื่อมต่อกับ peer โดยใช้ host และ port ที่กำหนด.
            self.peers.append(peer_socket) #  เพิ่ม socket ของ peer ลงในลิสต์ peers
            print(f"Connected to peer {peer_host}:{peer_port}") #  แสดงข้อความว่าเชื่อมต่อกับ peer แล้ว

            # เริ่ม thread สำหรับรับข้อมูลจาก peer นี้
            peer_thread = threading.Thread(target=self.handle_client, args=(peer_socket,)) # สร้าง thread ใหม่สำหรับจัดการกับการเชื่อมต่อนี้
            peer_thread.start() # เริ่ม thread สำหรับจัดการการเชื่อมต่อ

        except Exception as e: # จับข้อผิดพลาดถ้ามี
            print(f"Error connecting to peer: {e}") # แสดงข้อความข้อผิดพลาด

    def broadcast(self, message): # ฟังก์ชันสำหรับส่งข้อความไปยังทุก peer ที่เชื่อมต่ออยู่
        # ส่งข้อมูลไปยังทุก peer ที่เชื่อมต่ออยู่
        for peer_socket in self.peers: #วนซ้ำผ่านทุก peer ที่เชื่อมต่ออยู่
            try: #
                peer_socket.send(json.dumps(message).encode('utf-8')) #  ส่งข้อความที่แปลงเป็น JSON และเข้ารหัสเป็น UTF-8 ไปยัง peer
            except Exception as e: # เริ่มบล็อกการตรวจจับข้อผิดพลาด
                print(f"Error broadcasting to peer: {e}") # แสดงข้อความข้อผิดพลาด
                self.peers.remove(peer_socket) # ลบ peer ที่มีข้อผิดพลาดออกจากลิสต์ peers

    def process_message(self, message): # ฟังก์ชันสำหรับประมวลผลข้อความที่ได้รับ
        # ประมวลผลข้อความที่ได้รับ
        if message['type'] == 'transaction': # ตรวจสอบประเภทของข้อความว่าคือ transaction หรือไม่
            print(f"Received transaction: {message['data']}") # แสดงข้อความเมื่อได้รับ transaction
            self.add_transaction(message['data']) #  เพิ่ม transaction ที่ได้รับลงในรายการ transactions
        else:                                      # ถ้าประเภทของข้อความไม่ใช่ transaction
            print(f"Received message: {message}") # : แสดงข้อความที่ได้รับ

    def add_transaction(self, transaction): #  ฟังก์ชันสำหรับเพิ่ม transaction ใหม่
        # เพิ่ม transaction ใหม่และบันทึกลงไฟล์
        self.transactions.append(transaction) # เพิ่ม transaction ใหม่ลงในรายการ transactions
        self.save_transactions() # บันทึก transactions ลงไฟล์
        print(f"Transaction added and saved: {transaction}") # แสดงข้อความเมื่อเพิ่ม transaction ใหม่และบันทึกแล้ว

    def create_transaction(self, recipient, amount): # ฟังก์ชันสำหรับสร้าง transaction ใหม่
        # สร้าง transaction ใหม่
        transaction = { # สร้าง transaction ใหม่
            'sender': self.wallet_address, #สร้าง transaction ใหม่
            'recipient': recipient, #สร้าง transaction ใหม่
            'amount': amount  #สร้าง transaction ใหม่
        }
        self.add_transaction(transaction) # เพิ่ม transaction ใหม่ลงในรายการ transactions
        self.broadcast({'type': 'transaction', 'data': transaction}) # ส่ง transaction ใหม่ไปยังทุก peer ที่เชื่อมต่ออยู่

    def save_transactions(self): # ฟังก์ชันสำหรับบันทึก transactions ลงไฟล์
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f: # เปิดไฟล์สำหรับเขียน
            json.dump(self.transactions, f) # เขียนรายการ transactions ลงในไฟล์ในรูปแบบ JSON

    def load_transactions(self): # ฟังก์ชันสำหรับโหลด transactions จากไฟล์
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file): # ตรวจสอบว่าไฟล์ transactions มีอยู่หรือไม่
            with open(self.transaction_file, 'r') as f: # เปิดไฟล์สำหรับอ่าน
                self.transactions = json.load(f) # โหลดรายการ transactions จากไฟล์
            print(f"Loaded {len(self.transactions)} transactions from file.") # แสดงข้อความเมื่อโหลด transactions จากไฟล์สำเร็จ

if __name__ == "__main__": # ตรวจสอบว่ากำลังรันสคริปต์นี้โดยตรง (ไม่ใช่การนำเข้าเป็นโมดูล)
    if len(sys.argv) != 2: # ตรวจสอบจำนวนอาร์กิวเมนต์ที่ได้รับ
        print("Usage: python p2p.py <port>") # แสดงข้อความการใช้งานที่ถูกต้อง
        sys.exit(1) # ออกจากโปรแกรมด้วยสถานะผิดพลาด
     
    port = int(sys.argv[1]) # รับค่า port จากอาร์กิวเมนต์
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก , สร้าง instance ของ Node โดยใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start() # เริ่มต้นการทำงานของโหนด
    
    while True: # ทำงานวนซ้ำตลอดเวลาเพื่อรับคำสั่งจากผู้ใช้
        print("\n1. Connect to a peer") # แสดงตัวเลือกการเชื่อมต่อกับ peer
        print("2. Create a transaction") #  แสดงตัวเลือกการสร้าง transaction
        print("3. View all transactions") #  แสดงตัวเลือกการดูรายการ transactions ทั้งหมด
        print("4. View my wallet address") # แสดงตัวเลือกการดู wallet address ของตนเอง
        print("5. Exit") # แสดงตัวเลือกการออกจากโปรแกรม
        choice = input("Enter your choice: ") # รับค่าตัวเลือกจากผู้ใช้
        
        if choice == '1': # ถ้าผู้ใช้เลือกตัวเลือก 1
            peer_host = input("Enter peer host to connect: ") # รับค่า host ของ peer ที่ต้องการเชื่อมต่อ
            peer_port = int(input("Enter peer port to connect: ")) # รับค่า port ของ peer ที่ต้องการเชื่อมต่อ
            node.connect_to_peer(peer_host, peer_port) # เชื่อมต่อกับ peer ที่ระบุ
        elif choice == '2':        # ถ้าผู้ใช้เลือกตัวเลือก 2
            recipient = input("Enter recipient wallet address: ") # รับค่า wallet address ของผู้รับ
            amount = float(input("Enter amount: ")) # รับจำนวนเงินที่ต้องการส่ง
            node.create_transaction(recipient, amount) # : สร้าง transaction ใหม่
        elif choice == '3':   # ถ้าผู้ใช้เลือกตัวเลือก 3
            print("All transactions:") #  แสดงข้อความ "All transactions
            for tx in node.transactions: # วนซ้ำผ่านรายการ transactions ทั้งหมด
                print(tx) # แสดงรายละเอียดของ transaction
        elif choice == '4':    # ถ้าผู้ใช้เลือกตัวเลือก 4
            print(f"Your wallet address is: {node.wallet_address}") # แสดง wallet address ของผู้ใช้
        elif choice == '5':  # ถ้าผู้ใช้เลือกตัวเลือก 5
            break  # หยุดการวนซ้ำและออกจากโปรแกรม
        else:  # ถ้าผู้ใช้เลือกตัวเลือกที่ไม่ถูกต้อง
            print("Invalid choice. Please try again.") #  แสดงข้อความว่าเลือกไม่ถูกต้อง

    print("Exiting...")  #  เมื่อออกจากโปรแกรม