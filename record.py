import socket
import struct
import csv
import os
import keyboard
import winsound
from datetime import datetime

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"
UDP_PORT = 20778
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
FLAG_FILE = "record.flag"
os.makedirs(DATA_DIR, exist_ok=True)

# --- SOCKET SETUP ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(1.0)
    print(f"✅ PITWALL CONNECTED TO SIMHUB ON PORT {UDP_PORT}")
except Exception as e:
    print(f"❌ BIND ERROR: {e}")

# --- GLOBAL STATES ---
is_recording = False
csv_filename = None
current_lap = 1
current_sector = 0
wear_data = [0.0, 0.0, 0.0, 0.0]
damage_data = [0, 0, 0]

def start_recording():
    global is_recording, csv_filename
    is_recording = True
    session_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = os.path.join(DATA_DIR, f"f1_25_pro_{session_time}.csv")

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp", "Lap", "Sector", "Speed (km/h)", "Throttle (%)", "Brake (%)", "Steering (%)",
            "Temp_RL", "Temp_RR", "Temp_FL", "Temp_FR",
            "Wear_RL", "Wear_RR", "Wear_FL", "Wear_FR",
            "FW_Damage", "RW_Damage", "Engine_Damage"
        ])

    print(f"\n[🟢 STARTED] Recording: {os.path.basename(csv_filename)}")
    try:
     winsound.PlaySound("assets/incident.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
    except:pass

def stop_recording():
    global is_recording
    is_recording = False
    print("\n[🔴 STOPPED] Data saved. BOX BOX!")
    try:
     winsound.PlaySound("assets/supermax.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
    except:pass

# --- HOTKEY ---
keyboard.add_hotkey('F9', lambda: os.remove(FLAG_FILE) if os.path.exists(FLAG_FILE) else open(FLAG_FILE, 'w').close())

print("🛡️ F1 25 Analyzer Service Active...")
print("👉 Press 'F9' to Start/Stop Recording")

# --- MAIN LOOP ---
while True:
    try:
        flag_exists = os.path.exists(FLAG_FILE)
        if flag_exists and not is_recording:
            start_recording()
        elif not flag_exists and is_recording:
            stop_recording()

        data, addr = sock.recvfrom(2048)

        if len(data) < 29:
            continue

        header = struct.unpack_from('<HBBBBBQfII BB', data, 0)
        packet_id = header[5]
        player_index = header[10]

        # 🏁 LAP DATA (FIXED OFFSETS)
        if packet_id == 2:
                try:
                    # Player index header mein 27th byte par hota hai
                    player_index = data[27]
                    
                    # Official C++ struct ke hisab se har gaadi ka block 57 bytes ka hai
                    car_lap_size = 57 
                    
                    # Header (29) + Player Index ki position tak jump
                    base_lap = 29 + (player_index * car_lap_size)

                    # Exact byte offsets for F1 25:
                    # m_currentLapNum = base + 33
                    # m_sector = base + 36
                    lap = data[base_lap + 33]
                    sector = data[base_lap + 36] 

                    # Sanity check to avoid menu/loading glitches
                    if 0 < lap < 150:
                        current_lap = lap
                        current_sector = sector
                except Exception:
                    pass

        # 🛠️ DAMAGE DATA (FIXED FOR F1 25)
        elif packet_id == 10:
            # F1 25 Spec: Each car block is 46 bytes
            car_damage_size = 46 
            base = 29 + (player_index * car_damage_size)

            # ✅ Tyre wear (Starts at base + 0, 4 floats = 16 bytes)
            wear = struct.unpack_from('<ffff', data, base)
            wear_data = [round(w, 1) for w in wear]

            # ✅ Correct Damage Offsets for F1 25:
            # Skip: Wear(16) + TyreDmg(4) + BrakesDmg(4) + Blisters(4) = 28 bytes
            damage_start = base + 28
            damage_data = [
                data[damage_start],      # Front Left Wing (Offset 28)
                data[damage_start + 2],  # Rear Wing (Offset 30)
                data[damage_start + 13]  # Engine Damage (Offset 41)
            ]

        # 🏎️ TELEMETRY DATA (FIXED TEMP OFFSETS)
        elif packet_id == 6 and is_recording and csv_filename:
            base = 29 + player_index * 60

            speed = struct.unpack_from('<H', data, base)[0]
            thr = int(struct.unpack_from('<f', data, base + 2)[0] * 100)
            steer = int(struct.unpack_from('<f', data, base + 6)[0] * 100)
            brk = int(struct.unpack_from('<f', data, base + 10)[0] * 100)

            # ✅ CORRECT TEMP LOCATION
            t_rl = data[base + 25]
            t_rr = data[base + 26]
            t_fl = data[base + 27]
            t_fr = data[base + 28]

            now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    now, current_lap, current_sector + 1, speed,
                    thr, brk, steer,
                    t_rl, t_rr, t_fl, t_fr,
                    wear_data[0], wear_data[1], wear_data[2], wear_data[3],
                    damage_data[0], damage_data[1], damage_data[2]
                ])

            print(f"REC 🔴 | Lap: {current_lap} | Spd: {speed} | Thr: {thr}%", end="\r")

    except socket.timeout:
        continue
    except Exception as e:
        print("❌ ERROR:", e)