import streamlit as st
import requests
import pandas as pd
import altair as alt

API_URL = "http://127.0.0.1:8000/api/v1/monitoring/dashboard"

st.set_page_config(page_title="Dashboard de Monitoramento", layout="wide")
st.title("📊 Dashboard de Monitoramento")

try:
    response = requests.get(API_URL)
    data = response.json()
except Exception as e:
    st.error(f"Erro ao conectar com a API: {e}")
    st.stop()

st.subheader("🔹 Métricas Atuais")
metrics = data["current_metrics"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Requisições", metrics["total_requests"])
col2.metric("Taxa de Sucesso", f"{metrics['success_rate'] * 100:.2f}%")
col3.metric("Tempo Médio de Resposta", f"{metrics['avg_response_time']:.2f} ms")
col4.metric("Usuários Ativos", metrics["active_users"])

col5, col6, col7 = st.columns(3)
col5.metric("Erro 5xx", f"{metrics['error_rate_5xx'] * 100:.2f}%")
col6.metric("Erro 4xx", f"{metrics['error_rate_4xx'] * 100:.2f}%")
col7.metric("Logins Falhos", f"{metrics['failed_logins_rate'] * 100:.2f}%")

st.caption(f"📅 Última atualização: {metrics['current_timestamp']}")
st.caption(f"Fonte de dados: {metrics['data_source']}")

st.subheader("📈 Requisições por Hora")
requests_df = pd.DataFrame(data["historical_data"]["http_requests_timeline"])
requests_df["timestamp"] = pd.to_datetime(requests_df["timestamp"])

chart = alt.Chart(requests_df).mark_line(point=True).encode(
    x="timestamp:T",
    y="requests_count:Q",
    tooltip=["timestamp", "requests_count"]
).properties(height=300)

st.altair_chart(chart, use_container_width=True)

st.subheader("⏱️ Tempos de Resposta (p50, p95, p99)")
response_df = pd.DataFrame(data["historical_data"]["response_times_timeline"])
response_df["timestamp"] = pd.to_datetime(response_df["timestamp"])
response_df = response_df.melt(id_vars=["timestamp"], var_name="percentil", value_name="tempo")

chart2 = alt.Chart(response_df).mark_line(point=True).encode(
    x="timestamp:T",
    y="tempo:Q",
    color="percentil:N",
    tooltip=["timestamp", "percentil", "tempo"]
).properties(height=300)

st.altair_chart(chart2, use_container_width=True)

st.subheader("🖥️ Uso de Sistema")
sys_df = pd.DataFrame(data["historical_data"]["system_metrics_timeline"])
sys_df["timestamp"] = pd.to_datetime(sys_df["timestamp"])
sys_df = sys_df.melt(id_vars=["timestamp"], var_name="métrica", value_name="percentual")

sys_df["tempo_metrica"] = sys_df["timestamp"].dt.strftime("%H:%M") + " - " + sys_df["métrica"]

chart3 = alt.Chart(sys_df).mark_bar(size=10).encode(
    x=alt.X("tempo_metrica:N", title=None, axis=None),
    y=alt.Y("percentual:Q", title="Uso (%)"),
    color=alt.Color("métrica:N", title="Métrica"),
    tooltip=["timestamp", "métrica", "percentual"]
).properties(height=300)

st.altair_chart(chart3, use_container_width=True)

st.subheader("⚠️ Eventos de Erro")
errors = data["historical_data"]["error_events"]
if errors:
    st.write(pd.DataFrame(errors))
else:
    st.info("Nenhum evento de erro registrado nas últimas 24h.")