const patientId = 1;
let currentView = "doctor";
let alertSocket;
let localStream;
let peerConnection;
let signalSocket;
let toastTimer;

const ICON_ALERT_TRIANGLE = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4 2.5 20h19L12 4Z"></path><path d="M12 10.5v4"></path><path d="M12 17.2h.01"></path></svg>';
const ICON_CHECK_CIRCLE = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M8.5 12.3 11 14.8 15.5 9.5"></path></svg>';
const ICON_CLOCK_SM = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 7.5V12l3 2"></path></svg>';

const $ = (selector) => document.querySelector(selector);
const api = async (path, options = {}) => {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || "Une erreur est survenue.");
  }
  return response.status === 204 ? null : response.json();
};

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3200);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-MA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function showView(name) {
  currentView = name;
  document.querySelectorAll(".view").forEach((element) => element.classList.toggle("active", element.id === `${name}-view`));
  document.querySelectorAll(".nav-item").forEach((element) => element.classList.toggle("active", element.dataset.view === name));
  const labels = { doctor: ["ESPACE MEDECIN", "Bonjour, Dr. Benali"], patient: ["ESPACE PATIENT", "Mon suivi"], video: ["TELECONSULTATION", "Salle de consultation"] };
  $("#view-kicker").textContent = labels[name][0];
  $("#view-title").textContent = labels[name][1];
  $(".sidebar").classList.remove("open");
  if (name === "doctor") refreshDashboard();
  if (name === "patient") refreshPatientHistory();
}

function vitalMarkup(vital) {
  if (!vital) return ["--", "--", "--", "--"];
  return [`${vital.systolic}/${vital.diastolic}`, vital.heart_rate, vital.spo2, vital.temperature];
}

function updateVitalCards(vital) {
  const values = vitalMarkup(vital);
  document.querySelectorAll("#doctor-vitals .vital-card strong").forEach((element, index) => element.textContent = values[index]);
  $("#last-reading-time").textContent = vital ? formatDate(vital.recorded_at).split(" ").slice(-1)[0] : "Aucune";
}

function rowMarkup(vital, includeSource = true) {
  const sourceCell = includeSource
    ? `<td><span class="source-pill ${vital.source}">${vital.source === "simulated" ? "Simulee" : "Saisie patient"}</span></td>`
    : "";
  return `<tr><td>${formatDate(vital.recorded_at)}</td><td>${vital.systolic}/${vital.diastolic} mmHg</td><td>${vital.heart_rate} bpm</td><td>${vital.spo2}%</td><td>${vital.temperature} deg C</td>${sourceCell}</tr>`;
}

async function refreshHistory() {
  const vitals = await api(`/api/patients/${patientId}/vitals`);
  $("#doctor-history").innerHTML = vitals.length ? vitals.map((item) => rowMarkup(item)).join("") : `<tr><td colspan="6">Aucune constante enregistree.</td></tr>`;
  $("#patient-history").innerHTML = vitals.length ? vitals.map((item) => rowMarkup(item, false)).join("") : `<tr><td colspan="5">Aucune constante enregistree.</td></tr>`;
  updateVitalCards(vitals[0]);
}

async function refreshPatientHistory() {
  try { await refreshHistory(); } catch (error) { toast(error.message, true); }
}

function alertMarkup(alert) {
  const severity = alert.severity === "critical" ? "critical" : "";
  const action = alert.status === "open"
    ? `<button type="button" data-alert-id="${alert.id}" class="acknowledge">${ICON_CHECK_CIRCLE}<span>Acquitter l'alerte</span></button>`
    : `<span class="alert-done">${ICON_CHECK_CIRCLE}<span>Alerte acquittee</span></span>`;
  return `<article class="alert-item ${severity}">
    <div class="alert-item-head">
      <span class="alert-icon" aria-hidden="true">${ICON_ALERT_TRIANGLE}</span>
      <strong>${alert.patient_name}</strong>
      <span class="severity-pill">${alert.severity === "critical" ? "Critique" : "A surveiller"}</span>
    </div>
    <p>${alert.message}</p>
    <div class="alert-item-foot">
      <span class="alert-time">${ICON_CLOCK_SM}<span>${formatDate(alert.created_at)}</span></span>
      ${action}
    </div>
  </article>`;
}

async function refreshAlerts() {
  const alerts = await api("/api/alerts");
  const open = alerts.filter((alert) => alert.status === "open");
  $("#alert-count").textContent = open.length;
  $("#open-alerts").textContent = open.length.toString().padStart(2, "0");
  $("#alerts-list").innerHTML = alerts.length ? alerts.map(alertMarkup).join("") : `<p class="empty-state">Aucune alerte ouverte. Les seuils sont surveilles en continu.</p>`;
}

async function refreshDashboard() {
  try {
    const dashboard = await api("/api/dashboard");
    updateVitalCards(dashboard.latest_vital);
    $("#consent-state").textContent = dashboard.latest_consent?.accepted ? "Confirme" : "En attente";
    await Promise.all([refreshHistory(), refreshAlerts()]);
  } catch (error) { toast(`Chargement impossible : ${error.message}`, true); }
}

async function submitVital(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  Object.keys(payload).forEach((key) => payload[key] = Number(payload[key]));
  try {
    const result = await api(`/api/patients/${patientId}/vitals`, { method: "POST", body: JSON.stringify(payload) });
    const feedback = result.alert ? `Mesure enregistree. Alerte transmise : ${result.alert.message}.` : "Mesure enregistree et transmise au medecin.";
    $("#vital-feedback").textContent = feedback;
    toast(result.alert ? "Alerte clinique envoyee." : "Constantes envoyees.", Boolean(result.alert));
    await refreshDashboard();
  } catch (error) { $("#vital-feedback").textContent = error.message; toast(error.message, true); }
}

async function submitConsent(event) {
  event.preventDefault();
  try {
    await api(`/api/patients/${patientId}/consents`, { method: "POST", body: JSON.stringify({ accepted: $("#consent-check").checked, purpose: "Teleconsultation pedagogique et suivi des constantes simulees." }) });
    $("#consent-badge").textContent = "Confirme";
    $("#consent-badge").className = "tag";
    $("#consent-feedback").textContent = "Votre consentement a ete enregistre avec horodatage.";
    toast("Consentement enregistre.");
    refreshDashboard();
  } catch (error) { $("#consent-feedback").textContent = error.message; toast(error.message, true); }
}

async function acknowledgeAlert(id) {
  try { await api(`/api/alerts/${id}/acknowledge`, { method: "PATCH" }); toast("Alerte acquittee."); refreshAlerts(); } catch (error) { toast(error.message, true); }
}

function connectAlertSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  alertSocket = new WebSocket(`${protocol}://${location.host}/ws/alerts`);
  alertSocket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "alert") { toast(`Nouvelle alerte : ${payload.alert.message}`, true); refreshDashboard(); }
  };
  alertSocket.onclose = () => setTimeout(connectAlertSocket, 2500);
}

function waitForFrame(videoEl, timeoutMs = 4000) {
  return new Promise((resolve) => {
    if (typeof videoEl.requestVideoFrameCallback === "function") {
      const timer = setTimeout(() => resolve(false), timeoutMs);
      videoEl.requestVideoFrameCallback(() => { clearTimeout(timer); resolve(true); });
      return;
    }
    const start = performance.now();
    const check = () => {
      if (videoEl.videoWidth > 0 && videoEl.videoHeight > 0) return resolve(true);
      if (performance.now() - start > timeoutMs) return resolve(false);
      requestAnimationFrame(check);
    };
    check();
  });
}

function watchForNoSignal(videoEl, label) {
  waitForFrame(videoEl).then((hasFrame) => {
    if (!hasFrame) {
      $("#video-status").textContent = `Aucune image ${label} recue. Fermez les autres onglets ou applications qui utilisent la camera, puis cliquez sur Terminer et reessayez.`;
      toast(`Aucune image ${label}.`, true);
    }
  });
}

const CAMERA_CONSTRAINT_ATTEMPTS = [
  { video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24 } }, audio: true },
  { video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 15 } }, audio: true },
  { video: true, audio: true },
];
let cameraRetryCount = 0;

async function acquireCamera() {
  let lastError;
  for (const constraints of CAMERA_CONSTRAINT_ATTEMPTS) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

async function activateVideo() {
  if (localStream) { toast("La camera est deja active.", true); return; }
  const room = $("#room-name").value.trim();
  if (!room) { toast("Saisissez un code de consultation.", true); return; }
  cameraRetryCount = 0;
  try {
    localStream = await acquireCamera();
    localStream.getTracks().forEach((track) => {
      track.onended = () => { toast("Le flux camera ou microphone a ete interrompu.", true); endCall(); };
    });
    const localVideo = $("#local-video");
    localVideo.srcObject = localStream;
    localVideo.play?.().catch(() => {});
    $("#video-status").textContent = "Camera active. Connexion a la salle en cours.";
    watchForNoSignal(localVideo, "camera locale");
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    signalSocket = new WebSocket(`${protocol}://${location.host}/ws/signaling/${encodeURIComponent(room)}`);
    signalSocket.onopen = setupPeerConnection;
    signalSocket.onmessage = handleSignal;
    signalSocket.onclose = () => { if (localStream) $("#video-status").textContent = "Signalisation deconnectee."; };
  } catch (error) { $("#video-status").textContent = "Camera ou microphone indisponible. Autorisez-les puis reessayez."; toast("Impossible d'acceder a la camera.", true); }
}

async function retryCameraCapture() {
  if (!peerConnection || peerConnection.connectionState === "closed") return;
  cameraRetryCount += 1;
  try {
    localStream?.getTracks().forEach((track) => track.stop());
    localStream = await acquireCamera();
    localStream.getTracks().forEach((track) => {
      track.onended = () => { toast("Le flux camera ou microphone a ete interrompu.", true); endCall(); };
      const sender = peerConnection.getSenders().find((item) => item.track && item.track.kind === track.kind);
      if (sender) sender.replaceTrack(track);
    });
    const localVideo = $("#local-video");
    localVideo.srcObject = localStream;
    localVideo.play?.().catch(() => {});
    watchForOutboundVideo(peerConnection);
  } catch (error) {
    $("#video-status").textContent = "Nouvelle tentative de camera impossible. Autorisez l'acces puis cliquez sur Terminer et reessayez.";
  }
}

async function watchForOutboundVideo(pc, delayMs = 4500) {
  await new Promise((resolve) => setTimeout(resolve, delayMs));
  if (!pc || pc.connectionState === "closed") return;
  const stats = await pc.getStats();
  let sent = 0;
  stats.forEach((entry) => { if (entry.type === "outbound-rtp" && entry.kind === "video") sent = entry.packetsSent; });
  if (sent === 0) {
    if (cameraRetryCount < 1) {
      $("#video-status").textContent = "Aucune image camera transmise. Nouvelle tentative automatique en cours...";
      toast("Nouvelle tentative de camera en cours.", true);
      await retryCameraCapture();
      return;
    }
    $("#video-status").textContent = "Votre camera ne transmet toujours aucune image apres une nouvelle tentative. Fermez les autres programmes ou onglets qui l'utilisent (Teams, Zoom, un autre onglet SahaLink), vérifiez qu'elle n'est pas couverte ou desactivee, puis cliquez sur Terminer et reessayez.";
    toast("Votre camera est active mais ne transmet aucune image.", true);
  }
}

async function setupPeerConnection() {
  peerConnection?.close();
  peerConnection = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
  localStream.getTracks().forEach((track) => peerConnection.addTrack(track, localStream));
  watchForOutboundVideo(peerConnection);
  peerConnection.ontrack = (event) => {
    const remoteVideo = $("#remote-video");
    remoteVideo.srcObject = event.streams[0];
    remoteVideo.play?.().catch(() => { remoteVideo.muted = true; remoteVideo.play?.().catch(() => {}); });
    $("#remote-placeholder").hidden = true;
    $("#video-status").textContent = "Consultation connectee.";
    watchForNoSignal(remoteVideo, "du correspondant");
  };
  peerConnection.onicecandidate = (event) => { if (event.candidate && signalSocket?.readyState === WebSocket.OPEN) signalSocket.send(JSON.stringify({ type: "candidate", candidate: event.candidate })); };
  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);
  signalSocket.send(JSON.stringify({ type: "offer", sdp: offer }));
}

async function handleSignal(event) {
  const message = JSON.parse(event.data);
  if (!peerConnection || !message.type) return;
  if (message.type === "offer") {
    await peerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp));
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    signalSocket.send(JSON.stringify({ type: "answer", sdp: answer }));
  }
  if (message.type === "answer") await peerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp));
  if (message.type === "candidate") await peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
}

function endCall() {
  peerConnection?.close(); peerConnection = null;
  signalSocket?.close(); signalSocket = null;
  localStream?.getTracks().forEach((track) => track.stop()); localStream = null;
  $("#local-video").srcObject = null; $("#remote-video").srcObject = null; $("#remote-placeholder").hidden = false;
  $("#video-status").textContent = "Consultation terminee. Camera inactive.";
}

function toggleTrack(kind, button, activeText, mutedText) {
  const track = localStream?.getTracks().find((item) => item.kind === kind);
  if (!track) { toast("Activez d'abord la camera.", true); return; }
  track.enabled = !track.enabled;
  const label = button.querySelector("span");
  if (label) label.textContent = track.enabled ? activeText : mutedText;
  else button.textContent = track.enabled ? activeText : mutedText;
  button.setAttribute("aria-pressed", String(!track.enabled));
  button.classList.toggle("is-muted", !track.enabled);
}

function wireInteractions() {
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  document.querySelectorAll("[data-view-target]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.viewTarget)));
  $("#open-video-doctor").addEventListener("click", () => showView("video"));
  $("#open-video-patient").addEventListener("click", () => showView("video"));
  $("#alert-focus").addEventListener("click", () => { showView("doctor"); $("#alerts-panel").scrollIntoView({ behavior: "smooth", block: "center" }); });
  $("#vital-form").addEventListener("submit", submitVital);
  $("#consent-form").addEventListener("submit", submitConsent);
  $("#simulate-critical").addEventListener("click", () => { const form = $("#vital-form"); form.querySelector('[name="systolic"]').value = 188; form.querySelector('[name="diastolic"]').value = 122; form.querySelector('[name="heart_rate"]').value = 138; form.querySelector('[name="spo2"]').value = 89; form.querySelector('[name="temperature"]').value = 39.2; toast("Valeurs de cas degrade pre-remplies. Envoyez-les pour tester l'alerte."); });
  $("#alerts-list").addEventListener("click", (event) => { const target = event.target.closest(".acknowledge"); if (target) acknowledgeAlert(target.dataset.alertId); });
  $("#start-call").addEventListener("click", activateVideo);
  $("#end-call").addEventListener("click", endCall);
  $("#toggle-mic").addEventListener("click", (event) => toggleTrack("audio", event.currentTarget, "Micro actif", "Micro coupe"));
  $("#toggle-camera").addEventListener("click", (event) => toggleTrack("video", event.currentTarget, "Camera active", "Camera coupee"));
  $(".mobile-menu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
}

document.addEventListener("DOMContentLoaded", () => {
  $("#today-label").textContent = new Intl.DateTimeFormat("fr-MA", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
  wireInteractions(); connectAlertSocket(); refreshDashboard();
});

