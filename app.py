import streamlit as st
import pandas as pd
import math
from datetime import datetime

# ============================================================
# KUMBHSARTHI AI — VERSION 3
# AI-Powered Crowd, Traffic & Pilgrim Management System
#
# Prototype uses SIMULATED demonstration data.
# No live government / police / GPS / CCTV feeds are connected.
# ============================================================

st.set_page_config(
    page_title="KumbhSarthi AI",
    page_icon="🙏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Helpers
# -----------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def risk_from_values(crowd, utilization, incident_level=0):
    score = (
        crowd * 0.45
        + utilization * 0.40
        + incident_level * 15
    )

    if score >= 82:
        return "CRITICAL", "🔴", score
    if score >= 62:
        return "HIGH", "🟠", score
    if score >= 42:
        return "MODERATE", "🟡", score
    return "LOW", "🟢", score


def format_time(minutes):
    minutes = max(0, float(minutes))
    if minutes < 1:
        return "< 1 min"
    return f"{minutes:.1f} min"


def route_recommendation(crowd, utilization, accessibility=False, emergency=False):
    """
    Returns route recommendation based on the same shared state
    used by the authority decision engine.
    """
    route_a = {
        "name": "Route A — Main Road",
        "time": 18,
        "crowd": 45,
        "traffic": 55,
        "walking": 0.8,
        "shuttle": False,
        "accessibility": True,
    }

    route_b = {
        "name": "Route B — Diversion Corridor",
        "time": 24,
        "crowd": 25,
        "traffic": 30,
        "walking": 1.2,
        "shuttle": True,
        "accessibility": True,
    }

    route_c = {
        "name": "Route C — Pedestrian Priority Path",
        "time": 28,
        "crowd": 20,
        "traffic": 10,
        "walking": 1.9,
        "shuttle": False,
        "accessibility": False,
    }

    if accessibility:
        # Prefer accessible options.
        candidates = [route_a, route_b]
    else:
        candidates = [route_a, route_b, route_c]

    if emergency or crowd >= 80 or utilization >= 90:
        chosen = route_b
    elif crowd >= 65 or utilization >= 75:
        chosen = route_b
    else:
        chosen = route_a

    # Accessibility override if chosen route isn't accessible.
    if accessibility and not chosen["accessibility"]:
        chosen = route_b

    return chosen, candidates


def get_authority_actions(crowd, utilization, risk, incident):
    actions = []

    if risk == "CRITICAL":
        actions.extend([
            "Activate traffic diversion on the affected corridor.",
            "Increase shuttle frequency toward the lower-density zone.",
            "Restrict additional inflow into the critical zone until density falls.",
            "Alert field officers and control-room teams.",
        ])
    elif risk == "HIGH":
        actions.extend([
            "Prepare traffic diversion before the bottleneck forms.",
            "Increase monitoring frequency in the affected zone.",
            "Keep additional shuttle capacity ready.",
        ])
    elif risk == "MODERATE":
        actions.extend([
            "Continue close monitoring.",
            "Prepare an alternate route and shuttle contingency.",
        ])
    else:
        actions.append("Continue normal monitoring.")

    if utilization >= 85:
        actions.append("Road utilization is high — prioritize controlled vehicle entry.")

    if crowd >= 80:
        actions.append("Crowd density is high — use zone-level movement control.")

    if incident > 0:
        actions.append("Incident signal detected — dispatch the nearest response team.")

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(actions))


def get_pilgrim_message(crowd, utilization, risk):
    if risk == "CRITICAL":
        return (
            "The preferred corridor is under critical pressure. "
            "KumbhSarthi recommends an alternate route and shuttle support."
        )
    if risk == "HIGH":
        return (
            "Crowd or traffic is increasing. KumbhSarthi recommends "
            "the diversion corridor to reduce exposure to congestion."
        )
    if risk == "MODERATE":
        return (
            "Conditions are manageable, but congestion may increase. "
            "Keep the alternate route available."
        )
    return "Conditions are currently manageable. The main route is suitable."


# -----------------------------
# Session state
# -----------------------------
defaults = {
    "vehicles": 50,
    "capacity": 100,
    "incoming_per_min": 5.0,
    "crowd": 65,
    "incident": 0,
    "shuttles": 24,
    "scenario": "Normal",
    "source": "Nashik Railway Station",
    "destination": "Ram Kund",
    "accessibility": False,
    "language": "English",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_system():
    for key, value in defaults.items():
        st.session_state[key] = value


def normal_scenario():
    st.session_state.vehicles = 50
    st.session_state.capacity = 100
    st.session_state.incoming_per_min = 5.0
    st.session_state.crowd = 65
    st.session_state.incident = 0
    st.session_state.shuttles = 24
    st.session_state.scenario = "Normal"


def crowd_surge_scenario():
    st.session_state.vehicles = 82
    st.session_state.capacity = 100
    st.session_state.incoming_per_min = 8.0
    st.session_state.crowd = 90
    st.session_state.incident = 1
    st.session_state.shuttles = 18
    st.session_state.scenario = "Sudden Crowd Surge"


def traffic_surge_scenario():
    st.session_state.vehicles = 95
    st.session_state.capacity = 100
    st.session_state.incoming_per_min = 7.0
    st.session_state.crowd = 82
    st.session_state.incident = 0
    st.session_state.shuttles = 16
    st.session_state.scenario = "Traffic Surge"


def incident_scenario():
    st.session_state.vehicles = 88
    st.session_state.capacity = 100
    st.session_state.incoming_per_min = 6.0
    st.session_state.crowd = 86
    st.session_state.incident = 2
    st.session_state.shuttles = 14
    st.session_state.scenario = "Incident Detected"


# -----------------------------
# Calculations — ONE SHARED STATE
# -----------------------------
vehicles = int(st.session_state.vehicles)
capacity = max(1, int(st.session_state.capacity))
incoming = float(st.session_state.incoming_per_min)
crowd = int(st.session_state.crowd)
incident = int(st.session_state.incident)

utilization = clamp((vehicles / capacity) * 100, 0, 150)

predicted_10 = vehicles + incoming * 10
time_to_capacity = (
    (capacity - vehicles) / incoming if incoming > 0 and vehicles < capacity else 0
)

predicted_utilization = clamp((predicted_10 / capacity) * 100, 0, 150)
future_crowd = clamp(crowd + max(0, incoming - 4) * 2.2 + incident * 4, 0, 100)

risk, risk_icon, risk_score = risk_from_values(
    max(crowd, future_crowd),
    max(utilization, min(predicted_utilization, 100)),
    incident,
)

actions = get_authority_actions(crowd, utilization, risk, incident)
chosen_route, routes = route_recommendation(
    crowd,
    utilization,
    st.session_state.accessibility,
    risk == "CRITICAL",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.45rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #566573;
        margin-top: 0.15rem;
    }
    .flow-box {
        background: linear-gradient(90deg, #eef6ff, #f5f9ff);
        padding: 14px 18px;
        border-radius: 12px;
        border: 1px solid #d9e8f7;
        font-weight: 650;
    }
    .risk-box {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin: 8px 0 18px 0;
    }
    .small-note {
        color: #68737d;
        font-size: 0.88rem;
    }
    .route-card {
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #dfe5ea;
        background: #fafafa;
        margin-bottom: 10px;
    }
    .recommended {
        border: 2px solid #4a90e2;
        background: #f1f7ff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 🙏 KumbhSarthi AI")
    st.markdown("### Intelligent Kumbh Control Centre")
    st.info(
        "AI-powered crowd, traffic, mobility and pilgrim management system."
    )

    mode = st.selectbox(
        "System Mode",
        ["Authority Control Centre", "Pilgrim Assistant"],
        key="system_mode",
    )

    st.markdown("---")
    st.markdown("### 🎬 Demo Scenarios")

    if st.button("🟢 Normal Conditions", use_container_width=True):
        normal_scenario()
        st.rerun()

    if st.button("🚨 Sudden Crowd Surge", use_container_width=True):
        crowd_surge_scenario()
        st.rerun()

    if st.button("🚗 Traffic Surge", use_container_width=True):
        traffic_surge_scenario()
        st.rerun()

    if st.button("🚑 Incident Detected", use_container_width=True):
        incident_scenario()
        st.rerun()

    if st.button("🔄 Reset System", use_container_width=True):
        reset_system()
        st.rerun()

    st.markdown("---")
    st.markdown("### ℹ️ Prototype")
    st.caption(
        "This prototype uses simulated demonstration data. "
        "It is not connected to live CCTV, GPS, police, transport or government feeds."
    )

# -----------------------------
# Header
# -----------------------------
st.markdown(
    '<div class="main-title">🙏 KUMBHSARTHI AI</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">AI-Powered Crowd, Traffic & Pilgrim Management System</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="flow-box">
    🎯 One connected intelligence layer:
    <b>Detect → Predict → Decide → Guide → Re-route</b>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.scenario != "Normal":
    st.warning(
        f"🎬 **Demo Scenario Active:** {st.session_state.scenario} — "
        "all modules are using the same simulated system state."
    )

st.markdown("")

# -----------------------------
# Top live metrics
# -----------------------------
st.subheader("📊 Live Kumbh Situation")

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric("🚗 Active Vehicles", vehicles)

with m2:
    st.metric("👥 Crowd Density", f"{crowd}%")

with m3:
    st.metric("🛣️ Road Utilization", f"{utilization:.0f}%")

with m4:
    st.metric("⚠️ Risk Score", f"{risk_score:.0f}")

with m5:
    st.metric("🚌 Active Shuttles", st.session_state.shuttles)

# -----------------------------
# Intelligence map
# -----------------------------
st.subheader("🗺️ KumbhSarthi Intelligence Map")
st.caption(
    "Demonstration map showing simulated crowd zones, route points and facilities."
)

map_df = pd.DataFrame(
    [
        [20.0063, 73.7898, "Nashik Railway Station", 1],
        [20.0012, 73.7926, "Ram Kund", 5 if risk in ["HIGH", "CRITICAL"] else 3],
        [20.0055, 73.7870, "Diversion Corridor", 2],
        [20.0090, 73.7930, "Shuttle Hub", 2],
        [19.9975, 73.7960, "Medical / Help Point", 1],
    ],
    columns=["lat", "lon", "location", "risk"],
)

st.map(map_df[["lat", "lon"]], zoom=12, size="risk")

map_table = map_df[["location", "risk"]].copy()
map_table["Status"] = map_table["risk"].map(
    lambda x: "🔴 High" if x >= 5 else ("🟠 Watch" if x >= 3 else "🟢 Normal")
)
map_table = map_table.drop(columns=["risk"])
st.dataframe(map_table, use_container_width=True, hide_index=True)

# -----------------------------
# AI Decision Engine
# -----------------------------
st.subheader("🧠 KumbhSarthi AI Decision Engine")

if risk == "CRITICAL":
    box_class = "risk-box"
    headline = "🔴 CRITICAL RISK DETECTED"
    summary = (
        "KumbhSarthi predicts that current crowd and traffic conditions "
        "may create a serious bottleneck."
    )
elif risk == "HIGH":
    box_class = "risk-box"
    headline = "🟠 HIGH RISK DETECTED"
    summary = (
        "KumbhSarthi detects increasing pressure and recommends preventive action."
    )
elif risk == "MODERATE":
    box_class = "risk-box"
    headline = "🟡 MODERATE RISK"
    summary = "Conditions are manageable, but the system recommends close monitoring."
else:
    box_class = "risk-box"
    headline = "🟢 NORMAL CONDITIONS"
    summary = "Current crowd and traffic conditions are within manageable limits."

st.markdown(
    f"""
    <div class="{box_class}">
        <h3>{headline}</h3>
        <p>{summary}</p>
        <b>Prediction for next 10 minutes</b>
        <p>
            Crowd: <b>{future_crowd:.0f}%</b><br>
            Road utilization: <b>{predicted_utilization:.0f}%</b><br>
            Risk level: <b>{risk}</b>
        </p>
        <b>AI Model Assessment</b>
        <p>{risk_icon} {risk} operational-risk state</p>
    </div>
    """,
    unsafe_allow_html=True,
)

d1, d2 = st.columns(2)

with d1:
    st.markdown("### 🏛️ Recommended Authority Actions")
    for action in actions:
        st.write(f"• {action}")

with d2:
    st.markdown("### 🤖 Why did KumbhSarthi recommend this?")
    st.write(
        f"The recommendation is based on the shared state: "
        f"{crowd}% crowd density, {utilization:.0f}% current road utilization, "
        f"{predicted_utilization:.0f}% predicted utilization and "
        f"{incident} incident signal(s)."
    )

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🚦 Smart Traffic Control",
        "🔮 Future Prediction",
        "🧭 Pilgrim Assistant",
        "🚌 Mobility & Facilities",
        "🚨 Operations Centre",
    ]
)

# ============================================================
# TAB 1 — Traffic
# ============================================================
with tab1:
    st.header("🚦 Smart Traffic Control")
    st.caption(
        "Change traffic conditions here. The same values automatically affect "
        "prediction, AI decisions and pilgrim guidance."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Current Vehicles", vehicles)
        if st.button("➕ Add Incoming Vehicles", key="add_vehicle"):
            st.session_state.vehicles = clamp(
                st.session_state.vehicles + 10, 0, 200
            )
            st.rerun()

    with c2:
        st.metric("Available Capacity", capacity)
        if st.button("⚡ Traffic Surge +30", key="traffic_plus"):
            st.session_state.vehicles = clamp(
                st.session_state.vehicles + 30, 0, 200
            )
            st.rerun()

    with c3:
        st.metric("Road Utilization", f"{utilization:.0f}%")
        if st.button("↩️ Reset Traffic", key="reset_traffic"):
            st.session_state.vehicles = 50
            st.session_state.capacity = 100
            st.session_state.incoming_per_min = 5.0
            st.rerun()

    if utilization >= 100:
        st.error("🔴 TRAFFIC CRITICAL — Road capacity has been reached/exceeded.")
    elif utilization >= 80:
        st.warning("🟠 TRAFFIC HIGH — Road is approaching capacity.")
    elif utilization >= 60:
        st.warning("🟡 TRAFFIC MODERATE — Monitor traffic growth.")
    else:
        st.success("🟢 TRAFFIC NORMAL — Road has available capacity.")

# ============================================================
# TAB 2 — Prediction
# ============================================================
with tab2:
    st.header("🔮 Future Traffic Prediction")

    p1, p2, p3 = st.columns(3)

    with p1:
        new_capacity = st.number_input(
            "Road Capacity",
            min_value=20,
            max_value=500,
            value=int(st.session_state.capacity),
            step=10,
            key="capacity_input",
        )
        if new_capacity != st.session_state.capacity:
            st.session_state.capacity = int(new_capacity)
            st.rerun()

    with p2:
        new_incoming = st.number_input(
            "Incoming Vehicles / Minute",
            min_value=0.0,
            max_value=30.0,
            value=float(st.session_state.incoming_per_min),
            step=1.0,
            key="incoming_input",
        )
        if abs(new_incoming - st.session_state.incoming_per_min) > 0.001:
            st.session_state.incoming_per_min = float(new_incoming)
            st.rerun()

    with p3:
        st.metric("Estimated Time to Capacity", format_time(time_to_capacity))

    st.metric("Predicted Vehicles in 10 Minutes", f"{predicted_10:.0f}")

    if predicted_utilization >= 100:
        st.error(
            "🔴 CRITICAL — Predicted demand reaches/exceeds road capacity. "
            "Start diversion planning."
        )
    elif predicted_utilization >= 80:
        st.warning(
            "🟠 WARNING — Capacity may be reached soon. "
            "Prepare alternate traffic movement."
        )
    else:
        st.success(
            "🟢 NORMAL — Predicted traffic remains within available capacity."
        )

    st.markdown("### 📈 Prediction logic")
    st.code(
        "Predicted vehicles = current vehicles + incoming vehicles/min × 10",
        language="text",
    )

# ============================================================
# TAB 3 — Pilgrim Assistant
# ============================================================
with tab3:
    st.header("🧭 KumbhSarthi Pilgrim Assistant")
    st.caption(
        "The pilgrim module receives the same intelligence used by the authority centre."
    )

    r1, r2 = st.columns(2)

    with r1:
        source = st.selectbox(
            "📍 From",
            [
                "Nashik Railway Station",
                "CBS Bus Stand",
                "Parking Zone",
                "Shuttle Hub",
                "Nearby Accommodation",
            ],
            key="source_select",
        )
        st.session_state.source = source

    with r2:
        destination = st.selectbox(
            "🎯 To",
            [
                "Ram Kund",
                "Main Kumbh Zone",
                "Shahi Snan Zone",
                "Temple Area",
                "Medical / Help Centre",
            ],
            key="destination_select",
        )
        st.session_state.destination = destination

    st.session_state.accessibility = st.checkbox(
        "♿ Accessibility-friendly route",
        value=st.session_state.accessibility,
    )

    st.session_state.language = st.selectbox(
        "🌐 Guidance Language",
        ["English", "Hindi", "Marathi"],
        index=["English", "Hindi", "Marathi"].index(st.session_state.language),
    )

    st.markdown("---")

    st.markdown(
        f"### 🛣️ Journey: {st.session_state.source} → {st.session_state.destination}"
    )

    st.info(get_pilgrim_message(crowd, utilization, risk))

    if risk in ["HIGH", "CRITICAL"]:
        st.warning(
            f"🔄 **Dynamic re-routing active:** "
            f"conditions changed, so KumbhSarthi recommends **{chosen_route['name']}**."
        )
    else:
        st.success(
            f"✅ Recommended route: **{chosen_route['name']}**"
        )

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        st.metric("Estimated Time", f"{chosen_route['time']} min")
    with rc2:
        st.metric("Walking", f"{chosen_route['walking']:.1f} km")
    with rc3:
        st.metric("Route Crowd", f"{chosen_route['crowd']}%")
    with rc4:
        st.metric("Route Traffic", f"{chosen_route['traffic']}%")

    if chosen_route["shuttle"]:
        st.info("🚌 Shuttle recommended: use the nearest shuttle hub to reduce road congestion.")

    st.markdown("### 🛣️ Available Routes")

    for route in routes:
        is_selected = route["name"] == chosen_route["name"]
        css = "route-card recommended" if is_selected else "route-card"
        label = "⭐ AI RECOMMENDED" if is_selected else "Alternative"

        st.markdown(
            f"""
            <div class="{css}">
                <b>{route["name"]}</b> — {label}<br>
                ⏱️ {route["time"]} min &nbsp; | &nbsp;
                👥 Crowd {route["crowd"]}% &nbsp; | &nbsp;
                🚗 Traffic {route["traffic"]}% &nbsp; | &nbsp;
                🚶 {route["walking"]:.1f} km walking
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📍 Journey Safety Information")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.success("🚰 Water Point")
    with f2:
        st.success("🚻 Toilet")
    with f3:
        st.info("🏥 Medical Help")
    with f4:
        st.info("👮 Help / Police")

# ============================================================
# TAB 4 — Mobility & Facilities
# ============================================================
with tab4:
    st.header("🚌 Smart Mobility & Essential Facilities")

    st.markdown("### 🚌 Shuttle Management")

    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Active Shuttles", st.session_state.shuttles)
    with s2:
        recommended_shuttles = (
            30 if risk == "CRITICAL"
            else 27 if risk == "HIGH"
            else 24
        )
        st.metric("AI Suggested Shuttles", recommended_shuttles)
    with s3:
        delta = recommended_shuttles - st.session_state.shuttles
        st.metric("Additional Required", max(0, delta))

    if risk in ["HIGH", "CRITICAL"]:
        st.warning(
            "🚌 AI recommendation: increase shuttle frequency toward "
            "lower-density zones and reduce pressure on the affected corridor."
        )
    else:
        st.success("🚌 Current shuttle availability is sufficient for the simulated condition.")

    st.markdown("### 🏥 Essential Facilities")

    facilities = pd.DataFrame(
        [
            ["🚰 Water Point", "Ram Kund Zone", "Available", "Low"],
            ["🚻 Toilet", "Main Kumbh Zone", "Available", "Low"],
            ["🏥 Medical Centre", "Help Point A", "Available", "Medium"],
            ["👮 Police / Help", "Diversion Corridor", "Available", "Low"],
            ["🚌 Shuttle Hub", "Railway Station", "Active", "Medium"],
            ["🅿️ Parking", "Parking Zone", "Open", "Medium"],
        ],
        columns=["Facility", "Location", "Status", "Pressure"],
    )

    st.dataframe(facilities, use_container_width=True, hide_index=True)

    st.markdown("### ♿ Accessibility Support")
    st.write(
        "The pilgrim assistant can prioritize accessible routes and avoid "
        "routes that require unnecessary walking when accessibility mode is enabled."
    )

# ============================================================
# TAB 5 — Operations Centre
# ============================================================
with tab5:
    st.header("🚨 Kumbh Operations Centre")

    o1, o2 = st.columns(2)

    with o1:
        st.markdown("### ⚠️ Current Risk Zones")

        zone_data = pd.DataFrame(
            [
                ["Ram Kund", f"{future_crowd:.0f}%", risk],
                ["Main Kumbh Zone", f"{clamp(crowd - 8, 0, 100):.0f}%", "HIGH" if crowd >= 75 else "MODERATE"],
                ["Railway Approach", f"{clamp(utilization - 5, 0, 100):.0f}%", "HIGH" if utilization >= 80 else "NORMAL"],
                ["Diversion Corridor", "30%", "NORMAL"],
            ],
            columns=["Zone", "Estimated Crowd/Load", "Status"],
        )
        st.dataframe(zone_data, use_container_width=True, hide_index=True)

    with o2:
        st.markdown("### 📡 System Status")
        status_items = [
            ("Traffic Monitoring", "🟢 Active"),
            ("Crowd Intelligence", "🟢 Active"),
            ("Prediction Engine", "🟢 Active"),
            ("Decision Engine", "🟢 Active"),
            ("Pilgrim Guidance", "🟢 Active"),
            ("Dynamic Re-routing", "🟢 Active"),
        ]
        for name, status in status_items:
            st.write(f"**{name}:** {status}")

    st.markdown("---")

    st.markdown("### 🔁 End-to-End Intelligence Flow")

    flow_cols = st.columns(5)
    flow_steps = [
        ("1", "🔎 Detect", "Crowd + traffic"),
        ("2", "🔮 Predict", "Future pressure"),
        ("3", "🧠 Decide", "AI action"),
        ("4", "🧭 Guide", "Pilgrim advice"),
        ("5", "🔄 Re-route", "Continuous update"),
    ]

    for col, (num, title, desc) in zip(flow_cols, flow_steps):
        with col:
            st.markdown(f"### {title}")
            st.caption(desc)

    st.markdown("---")
    st.markdown("### 🧪 Demo Explanation")

    st.write(
        "For a competition demonstration, start with Normal Conditions. "
        "Then select 'Sudden Crowd Surge' from the sidebar. "
        "The shared state changes, the prediction changes, the AI risk level changes, "
        "authority actions change, and the pilgrim route automatically switches "
        "toward the diversion corridor."
    )

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")

now = datetime.now().strftime("%d %b %Y, %I:%M %p")

st.markdown(
    f"""
    <div style="text-align:center;">
        <b>🙏 KumbhSarthi AI</b><br>
        Detect → Predict → Decide → Guide → Re-route<br>
        <span class="small-note">
        Prototype using simulated data • Last local refresh: {now}
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
