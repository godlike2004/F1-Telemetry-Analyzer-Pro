import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import re

# ---------------------------
# 🔥 PAGE CONFIG
# ---------------------------
st.set_page_config(page_title="F1 Analyzer PRO", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #ff1744; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏎️ F1 Telemetry Analyzer PRO")
st.markdown("Welcome to the Pitwall. Analyze session data, tyre deg, and get AI insights from Bono.")
st.markdown("<br>", unsafe_allow_html=True) # Adds a little breathing room before the tabs

# ---------------------------
# 🎛️ SIDEBAR CONTROL PANEL
# ---------------------------
st.sidebar.title("🏎️ Pitwall Control")
st.sidebar.markdown("---")

st.sidebar.subheader("🎮 Live Recording")
FLAG_FILE = "record.flag"
is_recording = os.path.exists(FLAG_FILE)

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ Start", disabled=is_recording, use_container_width=True):
    open(FLAG_FILE, 'w').close()
    st.rerun()

if col2.button("⏹ Stop", disabled=not is_recording, use_container_width=True):
    if os.path.exists(FLAG_FILE):
        os.remove(FLAG_FILE)
    st.rerun()

# 📂 FILE SELECTOR
os.makedirs("data", exist_ok=True)
files = [f for f in os.listdir("data") if f.endswith(".csv")]
if not files:
    st.warning("No telemetry data found!")
    st.stop()

selected_file = st.sidebar.selectbox("Select Session:", sorted(files, reverse=True))
file_path = os.path.join("data", selected_file)

# ---------------------------
# 🔥 DATA LOAD & LOGIC
# ---------------------------
@st.cache_data
def load_data(path):
    data = pd.read_csv(path)
    #  Keep timestamp as string for the X-axis to avoid 1900 date bug
    data["Time_Ref"] = data["Timestamp"] 
    return data

df = load_data(file_path)

# Metrics Calculation
avg_speed = df["Speed (km/h)"].mean()
max_speed = df["Speed (km/h)"].max()
throttle_smoothness = df["Throttle (%)"].diff().abs().mean()

# Missing variables for AI Prompt calculation
avg_change = throttle_smoothness
if 'Brake (%)' in df.columns and 'Throttle (%)' in df.columns:
    corners = df[df['Brake (%)'] > 80] # Assuming >80% brake is a hard braking zone
    conflict = df[(df['Brake (%)'] > 0) & (df['Throttle (%)'] > 0)]
    avg_brake = df['Brake (%)'].mean()
else:
    corners = []
    conflict = []
    avg_brake = 0

# ---------------------------
# 🗂️ TABS SYSTEM
# ---------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🏁 Overview", "📈 Telemetry", "🛞 Tyre & Damage", "💾 Raw Data"])

# --- TAB 1: OVERVIEW ---
with tab1:
    st.header("🏁 Session Overview")
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Speed", f"{avg_speed:.1f} km/h")
    m2.metric("Max Speed", f"{max_speed:.0f} km/h")
    m3.metric("Throttle Smooth", f"{throttle_smoothness:.2f}")
    m4.metric("Data Points", len(df))

    st.markdown("---")
    st.subheader("🏁 Lap Analysis")

    if "Lap" in df.columns:

        laps = df.groupby("Lap")
        lap_summary = []

        for lap, data in laps:
            lap_time = len(data) / 60  # approx (60Hz)

            avg_speed_lap = data["Speed (km/h)"].mean()
            max_speed_lap = data["Speed (km/h)"].max()

            lap_summary.append({
                "Lap": lap,
                "Lap Time (s)": round(lap_time, 2),
                "Avg Speed": round(avg_speed_lap, 1),
                "Top Speed": max_speed_lap
            })

        lap_df = pd.DataFrame(lap_summary)
        st.dataframe(lap_df, use_container_width=True)

        # 🔥 BEST LAP
        best_lap = lap_df.loc[lap_df["Lap Time (s)"].idxmin()]
        st.success(f"🔥 Best Lap: {int(best_lap['Lap'])} | Time: {best_lap['Lap Time (s)']}s")
        selected_lap = st.selectbox("Analyze Lap", lap_df["Lap"])

        lap_data = df[df["Lap"] == selected_lap]
        st.line_chart(lap_data["Speed (km/h)"])

    # ---------------------------
    # 🧠 AI RACE ENGINEER 
    # ---------------------------
    st.markdown("---")
    st.subheader("🧠 AI Race Engineer")
    
    api_key = st.sidebar.text_input("Gemini API Key:", type="password")
    
    if not api_key:
        api_key = st.text_input("🔑 Enter Gemini API Key:", type="password")
        
    if st.button("🎙️ Ask Race Engineer (Gemini)"):
        if not api_key:
            st.error("Bhai, pehle API key toh daal!")
        else:
            with st.spinner("Bono is analyzing your telemetry... 🎧"):
                try:
                    # AI Configure 
                    genai.configure(api_key=api_key)
                    
                    # 🔥 Dynamic Model Fetching 🔥
                    
                    working_model = None
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            working_model = m.name
                            break 
                            
                    if not working_model:
                        st.error("Error: Tumhari API key par koi bhi Text Model active nahi hai. Nayi API key try karo.")
                    else:
                        
                        model = genai.GenerativeModel(working_model)
                        
                        # AI Prompt 
                        prompt = f"""
                        You are an expert F1 Race Engineer (like Peter Bonnington 'Bono'). 
                        Your driver just finished a stint. Analyze this telemetry data and give 3 short, brutal, but actionable pieces of advice.
                        Speak directly to the driver in a professional F1 radio tone.
                        
                        CRITICAL RULES FOR OUTPUT:
                        1. DO NOT use quotation marks ("") around your sentences. 
                        2. DO NOT write intro text like "Here is the analysis". Just speak directly.
                        3. Use numbered lists (1. 2. 3.) for your 3 points.
                        
                        Data:
                        - Average Speed: {df['Speed (km/h)'].mean():.1f} km/h
                        - Top Speed: {df['Speed (km/h)'].max():.0f} km/h
                        - Throttle Smoothness (Lower is better): {avg_change:.1f}
                        - Hard Braking Zones: {len(corners)}
                        - Instances of pressing Brake & Throttle together: {len(conflict)}
                        - Average Brake Pressure: {avg_brake:.1f}%
                        """
                        
                        # AI call 
                        response = model.generate_content(prompt)
                        
                        # ---------------------------
                        # 🎨 THE "NEXT LEVEL" RADIO UI 
                        # ---------------------------
                        
                        # 1. Remove literal quotation marks from AI's response
                        clean_text = response.text.replace('"', '').replace("'", "'")
                        
                        # 2. Highlight Bold Text 
                        formatted_text = re.sub(
                            r'\*\*(.*?)\*\*', 
                            r'<span style="color: #ffffff; font-weight: 700; background-color: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; margin: 0 2px;">\1</span>', 
                            clean_text
                        )
                        
                        # 3. Style the Numbers 
                        formatted_text = re.sub(
                            r'(\d+)\.\s', 
                            r'<br><br><div style="display:inline-block; background-color: #00D2BE; color: #151821; font-weight: 900; width: 24px; height: 24px; text-align: center; border-radius: 5px; margin-right: 10px; line-height: 24px; box-shadow: 0 2px 5px rgba(0,210,190,0.3);">\1</div>', 
                            formatted_text
                        )
                        
                        # 4. Handle remaining newlines properly
                        formatted_text = formatted_text.replace('\n', '<br>')
                        formatted_text = formatted_text.replace('<br><br><br>', '<br><br>') # Clean up extra spaces

                        # 5. Build the custom Pitwall Box 
                        custom_ui = f"""
<style>
@keyframes radioPulse {{
0% {{ box-shadow: 0 0 0 0 rgba(0, 210, 190, 0.4); }}
70% {{ box-shadow: 0 0 0 10px rgba(0, 210, 190, 0); }}
100% {{ box-shadow: 0 0 0 0 rgba(0, 210, 190, 0); }}
}}
.live-indicator {{
width: 12px; height: 12px; background-color: #00D2BE; border-radius: 50%;
display: inline-block; margin-right: 12px; animation: radioPulse 2s infinite;
}}
</style>
<div style="background: linear-gradient(145deg, #151821 0%, #1e2130 100%); border-left: 5px solid #00D2BE; border-radius: 10px; padding: 25px; box-shadow: 0 8px 32px rgba(0, 210, 190, 0.08); margin-top: 25px; margin-bottom: 25px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px;">
<div style="display: flex; align-items: center;">
<div class="live-indicator"></div>
<h3 style="margin: 0; color: #00D2BE; font-size: 1.2em; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 800;">Team Radio Incoming</h3>
</div>
<span style="background-color: rgba(0, 210, 190, 0.1); border: 1px solid rgba(0, 210, 190, 0.3); color: #00D2BE; padding: 4px 10px; border-radius: 6px; font-size: 0.75em; font-weight: bold; text-transform: uppercase;">
{working_model}
</span>
</div>
<div style="height: 1px; background: rgba(255,255,255,0.05); margin-bottom: 5px;"></div>
<div style="color: #c9d1d9; font-size: 1.05em; line-height: 1.7; letter-spacing: 0.3px;">
{formatted_text}
</div>
</div>
"""
                        
                        # Render the custom UI
                        st.markdown(custom_ui, unsafe_allow_html=True)
                        
                       
                        
                except Exception as e:
                    st.error(f"Error communicating with pitwall: {e}")


# --- TAB 2: TELEMETRY ---
with tab2:
    st.header("📈 Telemetry Analysis")
    st.markdown("---")
    if "Lap" in df.columns:

        # 🔥 Convert timestamp to seconds (clean axis)
        df["Time_Ref"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        df["Time_Ref"] = (df["Time_Ref"] - df["Time_Ref"].min()).dt.total_seconds()

        laps = sorted(df["Lap"].unique())
        sel_lap = st.selectbox("Select Lap:", ["All Laps"] + list(laps))
        lap_df = df if sel_lap == "All Laps" else df[df["Lap"] == sel_lap]

        # 🔥 View toggle
        view_mode = st.radio("Select View:", ["Combined", "Separate"], horizontal=True)

        # ---------------------------
        # 🔥 COMBINED GRAPH
        # ---------------------------
        if view_mode == "Combined":
            fig = px.line(
                lap_df,
                x="Time_Ref",
                y=["Speed (km/h)", "Throttle (%)", "Brake (%)"],
                title=f"Telemetry: Lap {sel_lap}",
                color_discrete_map={
                    "Speed (km/h)": "#00E5FF",
                    "Throttle (%)": "#00E676",
                    "Brake (%)": "#FF1744"
                }
            )

            fig.update_layout(
                template="plotly_dark",
                hovermode="x unified",
                xaxis_title="Time (sec)",
                xaxis=dict(nticks=20)  # 🔥 reduce crowding
            )

            st.plotly_chart(fig, use_container_width=True)

        # ---------------------------
        # 🔥 SEPARATE GRAPHS
        # ---------------------------
        else:
            fig1 = px.line(lap_df, x="Time_Ref", y="Speed (km/h)", title="Speed")
            fig2 = px.line(lap_df, x="Time_Ref", y="Throttle (%)", title="Throttle")
            fig3 = px.line(lap_df, x="Time_Ref", y="Brake (%)", title="Brake")

            for fig in [fig1, fig2, fig3]:
                fig.update_layout(
                    template="plotly_dark",
                    xaxis_title="Time (sec)",
                    xaxis=dict(nticks=20)
                )
                st.plotly_chart(fig, use_container_width=True)

        # ---------------------------
        # 🔥 LAP COMPARISON (PRO FEATURE)
        # ---------------------------
        st.markdown("---")
        st.subheader("🏁 Lap Comparison (Speed)")

        fig_lap = px.line(
            df,
            x="Time_Ref",
            y="Speed (km/h)",
            color="Lap",
            title="Speed Comparison Across Laps"
        )

        fig_lap.update_layout(
            template="plotly_dark",
            xaxis_title="Time (sec)",
            xaxis=dict(nticks=20)
        )

        st.plotly_chart(fig_lap, use_container_width=True)

# --- TAB 3: TYRE & DAMAGE ---
with tab3:
    st.subheader("🛞 Tyre Intelligence System")

    temp_cols = [c for c in df.columns if 'Temp_' in c]
    wear_cols = [c for c in df.columns if 'Wear_' in c]

    # ---------------------------
    # 🔥 ROW 1
    # ---------------------------
    col1, col2 = st.columns(2)

    with col1:
        if temp_cols:
            df_smooth = df.copy()
            df_smooth[temp_cols] = df[temp_cols].rolling(window=5, min_periods=1).mean()

            fig_temp = px.line(df_smooth, x="Time_Ref", y=temp_cols, title="Tyre Temperature Stability")

            fig_temp.update_layout(
                template="plotly_dark",
                yaxis_range=[60, 130],
                xaxis=dict(nticks=20)
            )

            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("No Temp data")

    with col2:
        if wear_cols:
            fig_wear = px.line(df, x="Time_Ref", y=wear_cols, title="Tyre Wear Progression")

            fig_wear.update_layout(
                template="plotly_dark",
                xaxis=dict(nticks=20)
            )

            st.plotly_chart(fig_wear, use_container_width=True)

    # ---------------------------
    # 🔥 ROW 2
    # ---------------------------
    st.markdown("---")
    col3, col4 = st.columns(2)

    # ✅ GRIP VS TEMP (FIXED)
    with col3:
        st.subheader("🧠 Real Grip vs Temperature (Per Tyre)")

        fig_real_grip = go.Figure()

        for col in temp_cols:
            grip = df[col].apply(lambda t: max(0, 5 - ((t - 90) ** 2) / 200))
            grip = grip.rolling(window=5, min_periods=1).mean()

            fig_real_grip.add_trace(go.Scatter(
                x=df["Time_Ref"],
                y=grip,
                mode='lines',
                name=col
            ))
        fig_real_grip.add_hline(y=4.5, line_dash="dash", line_color="green")
        fig_real_grip.add_hline(y=2.5, line_dash="dash", line_color="red")
        
        fig_real_grip.update_layout(
            template="plotly_dark",
            xaxis_title="Time (sec)",
            yaxis_title="Grip Level",
            xaxis=dict(nticks=20),
            yaxis=dict(range=[0, 5])
        )

        st.plotly_chart(fig_real_grip, use_container_width=True)

    # ✅ GRIP LOSS VS WEAR (FIXED)
    with col4:
        st.subheader("📉 Grip Loss vs Wear (Realistic)")

        wear_range = list(range(0, 101, 5))
        grip_loss = []

        for w in wear_range:
            if w < 30:
                grip_loss.append(100 - w * 0.1)
            elif w < 70:
                grip_loss.append(97 - (w - 30) * 0.2)
            else:
                grip_loss.append(89 - (w - 70) * 0.5)

        fig_deg = go.Figure()

        fig_deg.add_trace(go.Scatter(
            x=wear_range,
            y=grip_loss,
            mode='lines+markers',
            name='Grip %'
        ))

        fig_deg.update_layout(
            template="plotly_dark",
            xaxis_title="Tyre Wear (%)",
            yaxis_title="Grip (%)",
            yaxis=dict(range=[60, 100])
        )

        st.plotly_chart(fig_deg, use_container_width=True)


    # ---------------------------
    # 🔥 ROW 3: DAMAGE DASHBOARD (BIG 💀)
    # ---------------------------
    st.markdown("---")
    st.subheader("🏎️ Car Damage Analysis")

    d1, d2, d3 = st.columns(3)

    fw = df['FW_Damage'].iloc[-1] if 'FW_Damage' in df.columns else 0
    rw = df['RW_Damage'].iloc[-1] if 'RW_Damage' in df.columns else 0
    eng = df['Engine_Damage'].iloc[-1] if 'Engine_Damage' in df.columns else 0

    with d1:
        st.metric("Front Wing", f"{fw}%")
        st.progress(fw / 100)

    with d2:
        st.metric("Rear Wing", f"{rw}%")
        st.progress(rw / 100)

    with d3:
        st.metric("Engine", f"{eng}%")
        st.progress(eng / 100)
        
    # ---------------------------
    # 🔥 ALERT SYSTEM (INSIDE TAB3)
    # ---------------------------
    st.markdown("---")
    st.subheader("🚨 Tyre Alerts System")

    alerts = []

    for col in temp_cols:
        current_temp = df[col].iloc[-1]

        if current_temp > 105:
            alerts.append(f"🔴 {col} OVERHEATING ({current_temp:.1f}°C)")
        elif current_temp < 70:
            alerts.append(f"🔵 {col} TOO COLD ({current_temp:.1f}°C)")

    for col in temp_cols:
        grip = max(0, 5 - ((df[col].iloc[-1] - 90) ** 2) / 200)

        if grip < 2.5:
            alerts.append(f"🟡 {col} LOW GRIP ({grip:.2f})")

    # display
    if alerts:
        for alert in alerts:
            st.error(alert)
    else:
        st.success("✅ All tyres in optimal window")

# --- TAB 4: RAW DATA ---
with tab4:
    st.subheader("💾 Recorded Data Stream")
    st.dataframe(df, use_container_width=True)
    