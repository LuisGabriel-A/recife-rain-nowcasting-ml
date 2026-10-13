"use strict";

const fields = ["precipitation_mm", "temperature_c", "humidity_pct", "pressure_station_mb"];
const labels = ["Chuva em mm/h", "Temperatura em °C", "Umidade em %", "Pressão em mb"];
let thresholds = null;
const synthetic = Array.from({length: 7}, (_, i) => ({
  datetime_utc: `2020-06-01T0${i}:00:00Z`,
  precipitation_mm: [0, 0, 0, 0.2, 0.6, 1.0, 2.0][i],
  temperature_c: 25, humidity_pct: 85, pressure_station_mb: 1010,
}));
let examples = [];
let lastResult = null;
const byId = id => document.getElementById(id);
const formatTime = value => value ? new Date(value).toLocaleString("pt-BR", {timeZone: "UTC", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit"}) + " UTC" : "Aguardando consulta";

function resetResults() {
  lastResult = null;
  byId("download").disabled = true;
  byId("response-json").textContent = "";
  byId("forecast-context").textContent = "Entrada alterada. Consulte novamente para atualizar os horizontes.";
  showCards(null);
}

function renderHistory(history) {
  byId("history").replaceChildren();
  history.forEach((row, i) => {
    const tr = document.createElement("tr");
    const timeCell = document.createElement("td");
    const time = document.createElement("input");
    time.type = "datetime-local"; time.step = "3600"; time.required = true;
    time.value = new Date(row.datetime_utc).toISOString().slice(0, 16);
    time.setAttribute("aria-label", `Hora UTC, linha ${i + 1}`);
    time.dataset.field = "datetime_utc";
    timeCell.append(time); tr.append(timeCell);
    fields.forEach((field, j) => {
      const td = document.createElement("td");
      const input = document.createElement("input");
      input.type = "number"; input.step = "any"; input.required = true;
      input.value = row[field]; input.dataset.field = field;
      input.setAttribute("aria-label", `${labels[j]}, linha ${i + 1}`);
      if (field === "precipitation_mm" || field === "humidity_pct") input.min = "0";
      if (field === "humidity_pct") input.max = "100";
      if (field === "pressure_station_mb") input.min = "0.001";
      td.append(input); tr.append(td);
    });
    byId("history").append(tr);
  });
  byId("error").hidden = true;
  resetResults();
}

function showCards(result) {
  byId("predictions").replaceChildren();
  for (let i = 0; i < 6; i++) {
    const prediction = result ? result.predictions[i] : null;
    const card = document.createElement("article");
    card.className = "forecast-card" + (prediction?.alert ? " positive" : "");
    const head = document.createElement("div"); head.className = "card-head";
    const horizon = document.createElement("span"); horizon.className = "horizon"; horizon.textContent = `+${i + 1}h`;
    const decision = document.createElement("span"); decision.className = "decision";
    decision.textContent = prediction ? (prediction.alert ? "Alerta do modelo" : "Sem alerta") : "Aguardando";
    head.append(horizon, decision);
    const time = document.createElement("p"); time.className = "forecast-at"; time.textContent = formatTime(prediction?.forecast_at_utc);
    const score = document.createElement("span"); score.className = "score"; score.textContent = prediction ? prediction.probability.toFixed(3) : "—";
    const scoreLabel = document.createElement("span"); scoreLabel.className = "score-label"; scoreLabel.textContent = "score";
    const meter = document.createElement("div"); meter.className = "meter";
    // CSP allows external styles only; use a native progress element for dynamic values.
    const progress = document.createElement("progress"); progress.max = 1; progress.value = prediction?.probability ?? 0;
    progress.setAttribute("aria-label", `Score do horizonte +${i + 1}h`);
    meter.append(progress);
    const threshold = document.createElement("div"); threshold.className = "threshold";
    threshold.textContent = "Threshold " + (prediction ? prediction.decision_threshold.toFixed(2) : thresholds ? thresholds[i].toFixed(2) : "—");
    card.append(head, time, score, scoreLabel, meter, threshold);
    byId("predictions").append(card);
  }
}

async function request(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Não foi possível concluir a consulta.");
  return body;
}

byId("example").addEventListener("change", event => {
  const selected = event.target.value;
  renderHistory(selected === "synthetic" ? synthetic : examples[Number(selected)].observations);
  byId("example-note").textContent = selected === "synthetic"
    ? "Valores sintéticos para demonstrar a interface."
    : "Observações históricas do dataset local A301. Você pode editá-las. Não são dados ao vivo.";
});
byId("history").addEventListener("input", () => {
  resetResults();
  byId("example-note").textContent = "Entrada editada manualmente. As previsões serão calculadas com estes valores.";
});
byId("forecast-form").addEventListener("submit", async event => {
  event.preventDefault();
  byId("error").hidden = true;
  const observations = [...byId("history").rows].map(tr => {
    const row = {};
    for (const input of tr.querySelectorAll("input")) {
      row[input.dataset.field] = input.dataset.field === "datetime_utc"
        ? new Date(input.value + "Z").toISOString() : Number(input.value);
    }
    return row;
  });
  const payload = {observations};
  byId("request-json").textContent = JSON.stringify(payload, null, 2);
  byId("predict-button").disabled = true;
  // Prevent edits while a request is in flight so results always match the table.
  byId("example").disabled = true;
  byId("history").querySelectorAll("input").forEach(input => input.disabled = true);
  resetResults();
  byId("forecast-context").textContent = "Consultando os seis modelos…";
  try {
    lastResult = await request("/api/predict", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    showCards(lastResult);
    byId("forecast-context").textContent = "Previsão a partir de " + formatTime(lastResult.prediction_time_utc) + ".";
    byId("response-json").textContent = JSON.stringify(lastResult, null, 2);
    byId("download").disabled = false;
  } catch (error) {
    byId("error").textContent = error.message; byId("error").hidden = false;
    byId("forecast-context").textContent = "Consulta não realizada. Corrija a entrada e tente novamente.";
  } finally {
    byId("predict-button").disabled = false;
    byId("example").disabled = false;
    byId("history").querySelectorAll("input").forEach(input => input.disabled = false);
  }
});
byId("download").addEventListener("click", () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult, null, 2)], {type: "application/json"}));
  const link = document.createElement("a"); link.href = url; link.download = "recife-rain-previsao.json"; link.click();
  URL.revokeObjectURL(url);
});

renderHistory(synthetic);
byId("forecast-context").textContent = "Pronto para consultar. Os modelos utilizam apenas o histórico informado.";
Promise.all([request("/api/health"), request("/api/examples")]).then(([health, data]) => {
  byId("connection").textContent = `${health.horizons.length} modelos carregados · execução local`;
  thresholds = health.thresholds;
  if (!lastResult) showCards(null);
  examples = data.examples;
  examples.forEach((example, i) => {
    const option = document.createElement("option"); option.value = String(i); option.textContent = example.name;
    byId("example").append(option);
  });
}).catch(error => {
  byId("connection").textContent = "Conexão indisponível";
  byId("error").textContent = error.message; byId("error").hidden = false;
});
