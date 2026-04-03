import pandas as pd
import matplotlib.pyplot as plt
import os

# 🔥 AUTO PICK LATEST CSV
files = os.listdir("data")
files = [f for f in files if f.endswith(".csv")]

latest_file = sorted(files)[-1]
file_path = os.path.join("data", latest_file)

print("Using file:", file_path)

# 1️⃣ Load data
df = pd.read_csv(file_path)

# 2️⃣ Braking detection
brake_threshold = 20
df["Braking"] = df["Brake (%)"] > brake_threshold
braking_points = df[df["Braking"]]

# 3️⃣ Throttle smoothness
df["Throttle Change"] = df["Throttle (%)"].diff().abs()
avg_change = df["Throttle Change"].mean()

print(f"\nThrottle Smoothness Score: {avg_change:.2f}")

# 4️⃣ Lap detection
df["Lap"] = 1
lap = 1

for i in range(1, len(df)):
    if df["Speed (km/h)"][i] < 50 and df["Speed (km/h)"][i-1] > 100:
        lap += 1
    df.at[i, "Lap"] = lap

print("\nTotal Laps Detected:", lap)

# 5️⃣ Sector analysis
print("\nSector Analysis:")

lap_groups = df.groupby("Lap")

for lap_num, lap_data in lap_groups:

    n = len(lap_data)

    s1 = lap_data.iloc[:n//3]["Speed (km/h)"].mean()
    s2 = lap_data.iloc[n//3:2*n//3]["Speed (km/h)"].mean()
    s3 = lap_data.iloc[2*n//3:]["Speed (km/h)"].mean()

    print(f"Lap {lap_num}: S1={s1:.1f}, S2={s2:.1f}, S3={s3:.1f}")

# 6️⃣ Corner detection
corners = df[(df["Brake (%)"] > 30) & (df["Speed (km/h)"] < 150)]
print(f"\nCorners Detected: {len(corners)}")

# 7️⃣ Lap performance
lap_speeds = {}

for lap_num, lap_data in lap_groups:
    avg_speed = lap_data["Speed (km/h)"].mean()
    lap_speeds[lap_num] = avg_speed

print("\nLap Performance:")
for lap_num, speed in lap_speeds.items():
    print(f"Lap {lap_num}: Avg Speed = {speed:.2f}")

# 8️⃣ Best vs Worst lap
best_lap = max(lap_speeds, key=lap_speeds.get)
worst_lap = min(lap_speeds, key=lap_speeds.get)

best_data = df[df["Lap"] == best_lap]
worst_data = df[df["Lap"] == worst_lap]

# 9️⃣ Time loss detection
min_len = min(len(best_data), len(worst_data))

best_speed = best_data["Speed (km/h)"].values[:min_len]
worst_speed = worst_data["Speed (km/h)"].values[:min_len]

speed_diff = best_speed - worst_speed
loss_points = [i for i in range(len(speed_diff)) if speed_diff[i] < -20]

print(f"\nTime Loss Points Detected: {len(loss_points)}")

# 🔟 PERFORMANCE SCORE
score = 100

if df["Brake (%)"].mean() > 30:
    score -= 10

if avg_change > 20:
    score -= 10

speed_std = df["Speed (km/h)"].std()

if speed_std > 60:
    score -= 10

print(f"\n🔥 Performance Score: {score}/100")

# 1️⃣1️⃣ CONSISTENCY
print(f"\nSpeed Consistency (std): {speed_std:.2f}")

if speed_std > 60:
    print("⚠️ Driving is inconsistent")
else:
    print("✅ Driving is consistent")

# 1️⃣2️⃣ THROTTLE-BRAKE CONFLICT
conflict = df[(df["Throttle (%)"] > 20) & (df["Brake (%)"] > 20)]

print(f"\nThrottle-Brake Conflict Points: {len(conflict)}")

if len(conflict) > 50:
    print("⚠️ You are overlapping throttle and brake")
else:
    print("✅ Inputs are clean")

# 1️⃣3️⃣ AI INSIGHTS
print("\n🧠 AI Insights:")

if avg_change > 20:
    print("→ Smooth your throttle inputs")

if df["Brake (%)"].mean() > 30:
    print("→ You may be braking too much")

if len(conflict) > 50:
    print("→ Avoid pressing brake and throttle together")

if speed_std > 60:
    print("→ Maintain consistent speed through corners")

# 🔟 GRAPH
plt.figure(figsize=(12,6))

plt.plot(df["Speed (km/h)"], label="Speed")

plt.scatter(braking_points.index, braking_points["Speed (km/h)"],
            color='red', label="Braking", s=10)

plt.scatter(corners.index, corners["Speed (km/h)"],
            color='orange', label="Corners", s=10)

plt.plot(best_data["Speed (km/h)"].values, label=f"Best Lap {best_lap}")
plt.plot(worst_data["Speed (km/h)"].values, label=f"Worst Lap {worst_lap}")

plt.legend()
plt.title("F1 Telemetry Full AI Analysis")

plt.show()