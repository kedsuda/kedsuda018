#อธิบายแบบระเอียด
#ของp2p_sync.py

import socket  # โมดูลสำหรับการทำงานกับเครือข่าย
import threading  # โมดูลสำหรับการทำงานกับ thread
import json  # โมดูลสำหรับการทำงานกับข้อมูลในรูปแบบ JSON
import sys  # โมดูลสำหรับการทำงานกับตัวแปรและฟังก์ชันของ interpreter
import os  # โมดูลสำหรับการทำงานกับระบบไฟล์
import secrets  # โมดูลสำหรับการสร้างเลขสุ่มที่ปลอดภัย

class Node:
    def __init__(self, host, port):
        self.host = host  # กำหนด host ของ node
        self.port = port  # กำหนด port ของ node
        self.peers = []  # สร้างรายการสำหรับเก็บ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket แบบ TCP/IP
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ตั้งค่าให้ socket สามารถใช้งานที่อยู่ซ้ำได้
        self.transactions = []  # สร้างรายการสำหรับเก็บ transactions
        self.transaction_file = f"transactions_{port}.json"  # ตั้งชื่อไฟล์สำหรับบันทึก transactions โดยใช้ port เป็นส่วนหนึ่งของชื่อไฟล์
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address สำหรับ node นี้

    def generate_wallet_address(self):
        # สร้าง wallet address แบบง่ายๆ (ในระบบจริงจะซับซ้อนกว่านี้มาก)
        return '0x' + secrets.token_hex(20)  # สร้างที่อยู่กระเป๋าเงิน (wallet address) โดยใช้เลขสุ่มขนาด 20 ไบต์

    def start(self):
        # เริ่มต้นการทำงานของ node
        self.socket.bind((self.host, self.port))  # ผูก socket กับที่อยู่และ port
        self.socket.listen(1)  # เริ่มฟังการเชื่อมต่อใหม่
        print(f"Node listening on {self.host}:{self.port}")  # แสดงข้อความว่า node กำลังฟังที่ host และ port ใด
        print(f"Your wallet address is: {self.wallet_address}")  # แสดง wallet address ของ node

        self.load_transactions()  # โหลด transactions จากไฟล์ (ถ้ามี)

        # เริ่ม thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections)  # สร้าง thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread.start()  # เริ่มการทำงานของ thread

    def accept_connections(self):
        while True:
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()  # รอรับการเชื่อมต่อใหม่
            print(f"New connection from {address}")  # แสดงข้อความเมื่อมีการเชื่อมต่อใหม่

            # เริ่ม thread ใหม่สำหรับจัดการการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))  # สร้าง thread สำหรับจัดการการเชื่อมต่อที่ได้รับ
            client_thread.start()  # เริ่มการทำงานของ thread

    def handle_client(self, client_socket):
        while True:
            try:
                # รับข้อมูลจาก client
                data = client_socket.recv(1024)  # รับข้อมูลจาก client สูงสุด 1024 ไบต์
                if not data:
                    break  # ถ้าไม่ได้รับข้อมูล ให้หยุดการทำงาน
                message = json.loads(data.decode('utf-8'))  # แปลงข้อมูลที่ได้รับเป็น JSON

                self.process_message(message, client_socket)  # ประมวลผลข้อความที่ได้รับ

            except Exception as e:
                print(f"Error handling client: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาด
                break  # หยุดการทำงานเมื่อเกิดข้อผิดพลาด

        client_socket.close()  # ปิดการเชื่อมต่อ

    def connect_to_peer(self, peer_host, peer_port):
        try:
            # สร้างการเชื่อมต่อไปยัง peer
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket สำหรับเชื่อมต่อไปยัง peer
            peer_socket.connect((peer_host, peer_port))  # เชื่อมต่อไปยัง peer
            self.peers.append(peer_socket)  # เพิ่ม socket ของ peer ที่เชื่อมต่อไปยังรายการ peers
            print(f"Connected to peer {peer_host}:{peer_port}")  # แสดงข้อความว่าเชื่อมต่อกับ peer สำเร็จ

            # ขอข้อมูล transactions ทั้งหมดจาก peer ที่เชื่อมต่อ
            self.request_sync(peer_socket)  # ส่งคำขอซิงโครไนซ์ไปยัง peer

            # เริ่ม thread สำหรับรับข้อมูลจาก peer นี้
            peer_thread = threading.Thread(target=self.handle_client, args=(peer_socket,))  # สร้าง thread สำหรับจัดการการเชื่อมต่อกับ peer
            peer_thread.start()  # เริ่มการทำงานของ thread

        except Exception as e:
            print(f"Error connecting to peer: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาดในการเชื่อมต่อกับ peer

    def broadcast(self, message):
        # ส่งข้อมูลไปยังทุก peer ที่เชื่อมต่ออยู่
        for peer_socket in self.peers:
            try:
                peer_socket.send(json.dumps(message).encode('utf-8'))  # ส่งข้อมูลที่เข้ารหัสเป็น JSON ไปยัง peer
            except Exception as e:
                print(f"Error broadcasting to peer: {e}")  # แสดงข้อความเมื่อเกิดข้อผิดพลาดในการส่งข้อมูล
                self.peers.remove(peer_socket)  # ลบ peer ที่มีปัญหาออกจากรายการ peers

    def process_message(self, message, client_socket):
        # ประมวลผลข้อความที่ได้รับ
        if message['type'] == 'transaction':
            print(f"Received transaction: {message['data']}")  # แสดงข้อความเมื่อได้รับ transaction ใหม่
            self.add_transaction(message['data'])  # เพิ่ม transaction ใหม่ลงในรายการ transactions
        elif message['type'] == 'sync_request':
            self.send_all_transactions(client_socket)  # ส่ง transactions ทั้งหมดไปยัง node ที่ขอซิงโครไนซ์
        elif message['type'] == 'sync_response':
            self.receive_sync_data(message['data'])  # รับและประมวลผลข้อมูล transactions ที่ได้รับจากการซิงโครไนซ์
        else:
            print(f"Received message: {message}")  # แสดงข้อความเมื่อได้รับข้อความอื่นๆ ที่ไม่ใช่ transaction หรือ sync

    def add_transaction(self, transaction):
        # เพิ่ม transaction ใหม่และบันทึกลงไฟล์
        if transaction not in self.transactions:
            self.transactions.append(transaction)  # เพิ่ม transaction ใหม่ลงในรายการ transactions
            self.save_transactions()  # บันทึก transactions ลงไฟล์
            print(f"Transaction added and saved: {transaction}")  # แสดงข้อความว่า transaction ถูกเพิ่มและบันทึกแล้ว

    def create_transaction(self, recipient, amount):
        # สร้าง transaction ใหม่
        transaction = {
            'sender': self.wallet_address,  # ที่อยู่ผู้ส่ง
            'recipient': recipient,  # ที่อยู่ผู้รับ
            'amount': amount  # จำนวนเงิน
        }
        self.add_transaction(transaction)  # เพิ่ม transaction ใหม่ลงในรายการ transactions
        self.broadcast({'type': 'transaction', 'data': transaction})  # ส่ง transaction ใหม่ไปยังทุก peer

    def save_transactions(self):
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f:
            json.dump(self.transactions, f)  # บันทึก transactions ในรูปแบบ JSON ลงไฟล์

    def load_transactions(self):
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file):
            with open(self.transaction_file, 'r') as f:
                self.transactions = json.load(f)  # โหลด transactions จากไฟล์
            print(f"Loaded {len(self.transactions)} transactions from file.")  # แสดงข้อความว่าโหลด transactions จำนวนกี่รายการจากไฟล์

    def request_sync(self, peer_socket):
        # ส่งคำขอซิงโครไนซ์ไปยัง peer
        sync_request = json.dumps({"type": "sync_request"}).encode('utf-8')  # สร้างคำขอซิงโครไนซ์ในรูปแบบ JSON
        peer_socket.send(sync_request)  # ส่งคำขอซิงโครไนซ์ไปยัง peer

    def send_all_transactions(self, client_socket):
        # ส่ง transactions ทั้งหมดไปยังโหนดที่ขอซิงโครไนซ์
        sync_data = json.dumps({
            "type": "sync_response",
            "data": self.transactions
        }).encode('utf-8')  # สร้างข้อมูลซิงโครไนซ์ในรูปแบบ JSON
        client_socket.send(sync_data)  # ส่งข้อมูลซิงโครไนซ์ไปยังโหนดที่ขอ

    def receive_sync_data(self, sync_transactions):
        # รับและประมวลผลข้อมูล transactions ที่ได้รับจากการซิงโครไนซ์
        for tx in sync_transactions:
            self.add_transaction(tx)  # เพิ่ม transactions ที่ได้รับลงในรายการ transactions
        print(f"Synchronized {len(sync_transactions)} transactions.")  # แสดงข้อความว่าซิงโครไนซ์ transactions จำนวนกี่รายการ

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <port>")  # แสดงข้อความการใช้งานที่ถูกต้องถ้าผู้ใช้ไม่ได้ใส่ port
        sys.exit(1)
    
    port = int(sys.argv[1])
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start()  # เริ่มต้นการทำงานของ node
while True:  # เริ่มต้น loop ที่ไม่มีที่สิ้นสุด (ทำงานจนกว่าจะสั่งหยุด)
    print("\n1. Connect to a peer")  # แสดงตัวเลือกที่ 1: เชื่อมต่อกับ peer
    print("2. Create a transaction")  # แสดงตัวเลือกที่ 2: สร้าง transaction ใหม่
    print("3. View all transactions")  # แสดงตัวเลือกที่ 3: ดูรายการ transactions ทั้งหมด
    print("4. View my wallet address")  # แสดงตัวเลือกที่ 4: ดูที่อยู่กระเป๋าเงินของ node
    print("5. Exit")  # แสดงตัวเลือกที่ 5: ออกจากโปรแกรม
    choice = input("Enter your choice: ")  # รับตัวเลือกจากผู้ใช้

    if choice == '1':  # ถ้าผู้ใช้เลือกตัวเลือกที่ 1
        peer_host = input("Enter peer host to connect: ")  # รับที่อยู่ของ peer ที่ต้องการเชื่อมต่อ
        peer_port = int(input("Enter peer port to connect: "))  # รับ port ของ peer ที่ต้องการเชื่อมต่อ
        node.connect_to_peer(peer_host, peer_port)  # เชื่อมต่อไปยัง peer ที่ระบุโดยเรียกฟังก์ชัน connect_to_peer ของ node
    elif choice == '2':  # ถ้าผู้ใช้เลือกตัวเลือกที่ 2
        recipient = input("Enter recipient wallet address: ")  # รับที่อยู่กระเป๋าเงินของผู้รับ
        amount = float(input("Enter amount: "))  # รับจำนวนเงิน
        node.create_transaction(recipient, amount)  # สร้าง transaction ใหม่โดยเรียกฟังก์ชัน create_transaction ของ node
    elif choice == '3':  # ถ้าผู้ใช้เลือกตัวเลือกที่ 3
        print("All transactions:")  # แสดงข้อความ "All transactions:"
        for tx in node.transactions:  # วน loop ผ่านรายการ transactions ทั้งหมดใน node
            print(tx)  # แสดง transaction แต่ละรายการ
    elif choice == '4':  # ถ้าผู้ใช้เลือกตัวเลือกที่ 4
        print(f"Your wallet address is: {node.wallet_address}")  # แสดงที่อยู่กระเป๋าเงินของ node
    elif choice == '5':  # ถ้าผู้ใช้เลือกตัวเลือกที่ 5
        break  # หยุด loop และจบการทำงานของโปรแกรม
    else:  # ถ้าผู้ใช้เลือกตัวเลือกที่ไม่ถูกต้อง
        print("Invalid choice. Please try again.")  # แสดงข้อความว่าเลือกเมนูไม่ถูกต้อง

print("Exiting...")  # แสดงข้อความว่ากำลังออกจากโปรแกรม
